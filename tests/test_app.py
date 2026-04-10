from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from order_system import create_app
from order_system.db import get_db
from order_system.services import timestamp


class DsoOrderSystemTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(database_path),
                "DEMO_DATA": False,
                "SECRET_KEY": "test-secret",
            }
        )
        self.client = self.app.test_client()

        with self.app.app_context():
            db = get_db()
            customer_cursor = db.execute(
                """
                INSERT INTO customers (
                    name,
                    account_code,
                    contact_name,
                    contact_email,
                    billing_email,
                    settlement_due_days,
                    credit_limit_cents,
                    notes,
                    active,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "测试 DSO 客户",
                    "TEST-DSO",
                    "张三",
                    "sales@test.example",
                    "finance@test.example",
                    30,
                    500_000_00,
                    "测试客户",
                    1,
                    timestamp(),
                ),
            )
            product_cursor = db.execute(
                """
                INSERT INTO products (sku, name, unit, unit_price_cents, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("SCAN-TIP", "口扫探头耗材", "支", 9_800, timestamp()),
            )
            db.commit()
            self.customer_id = customer_cursor.lastrowid
            self.product_id = product_cursor.lastrowid

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _create_shipped_order(self) -> int:
        response = self.client.post(
            "/orders",
            data={
                "customer_id": str(self.customer_id),
                "po_number": "PO-TEST-001",
                "order_date": "2026-04-10",
                "delivery_date": "2026-04-12",
                "status": "shipped",
                "notes": "测试订单",
                "product_id": [str(self.product_id)],
                "item_name": [""],
                "item_unit": [""],
                "item_quantity": ["3"],
                "item_price": [""],
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            db = get_db()
            order = db.execute("SELECT id FROM orders LIMIT 1").fetchone()
            self.assertIsNotNone(order)
            return int(order["id"])

    def test_generate_statement_from_shipped_order(self) -> None:
        order_id = self._create_shipped_order()

        response = self.client.post(
            "/statements/generate",
            data={"customer_id": str(self.customer_id), "period_month": "2026-04"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            db = get_db()
            statement = db.execute("SELECT * FROM statements LIMIT 1").fetchone()
            self.assertIsNotNone(statement)
            self.assertEqual(statement["period_month"], "2026-04")
            self.assertEqual(statement["total_amount_cents"], 29_400)

            linked_order = db.execute(
                """
                SELECT o.status
                FROM orders o
                JOIN statement_orders so ON so.order_id = o.id
                WHERE o.id = ?
                """,
                (order_id,),
            ).fetchone()
            self.assertIsNotNone(linked_order)
            self.assertEqual(linked_order["status"], "monthly_billed")

        csv_response = self.client.get(f"/statements/{statement['id']}/export")
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("text/csv", csv_response.content_type)
        self.assertIn("结算单号".encode("utf-8"), csv_response.data)

    def test_settled_statement_closes_related_orders(self) -> None:
        order_id = self._create_shipped_order()
        self.client.post(
            "/statements/generate",
            data={"customer_id": str(self.customer_id), "period_month": "2026-04"},
            follow_redirects=True,
        )

        with self.app.app_context():
            db = get_db()
            statement = db.execute("SELECT * FROM statements LIMIT 1").fetchone()
            self.assertIsNotNone(statement)
            statement_id = int(statement["id"])

        response = self.client.post(
            f"/statements/{statement_id}/status",
            data={"status": "settled"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            db = get_db()
            statement = db.execute("SELECT status FROM statements WHERE id = ?", (statement_id,)).fetchone()
            order = db.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
            self.assertEqual(statement["status"], "settled")
            self.assertEqual(order["status"], "closed")


if __name__ == "__main__":
    unittest.main()
