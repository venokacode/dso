from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import create_app


def _as_decimal(value) -> Decimal:
    return Decimal(str(value))


def test_dso_monthly_settlement_flow(tmp_path):
    db_file = tmp_path / "dso_test.db"
    app = create_app(f"sqlite:///{db_file}")

    with TestClient(app) as client:
        customer = client.post(
            "/customers",
            json={"code": "DSO-ACME", "name": "Acme Hospital Group", "billing_cycle_day": 25},
        )
        assert customer.status_code == 201
        customer_id = customer.json()["id"]

        product = client.post(
            "/products",
            json={"sku": "LAB-001", "name": "Lab Consumables Pack", "unit_price": "199.90"},
        )
        assert product.status_code == 201
        product_id = product.json()["id"]

        order = client.post(
            "/orders",
            json={
                "customer_id": customer_id,
                "order_date": "2026-04-08",
                "items": [{"product_id": product_id, "quantity": 3}],
                "note": "DSO monthly purchase",
            },
        )
        assert order.status_code == 201
        order_data = order.json()
        assert order_data["status"] == "CONFIRMED"
        assert _as_decimal(order_data["subtotal"]) == Decimal("599.70")

        settlement = client.get(
            "/settlements/monthly",
            params={"customer_id": customer_id, "month": "2026-04"},
        )
        assert settlement.status_code == 200
        settlement_data = settlement.json()
        assert settlement_data["customer_code"] == "DSO-ACME"
        assert settlement_data["order_count"] == 1
        assert _as_decimal(settlement_data["total_due"]) == Decimal("599.70")
        assert settlement_data["due_date"] == "2026-05-25"

        settle_order = client.patch(
            f"/orders/{order_data['id']}/status",
            json={"status": "SETTLED"},
        )
        assert settle_order.status_code == 200

        settlement_after_paid = client.get(
            "/settlements/monthly",
            params={"customer_id": customer_id, "month": "2026-04"},
        )
        assert settlement_after_paid.status_code == 200
        settlement_after_paid_data = settlement_after_paid.json()
        assert settlement_after_paid_data["order_count"] == 0
        assert _as_decimal(settlement_after_paid_data["total_due"]) == Decimal("0.00")
