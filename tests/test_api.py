from __future__ import annotations

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(tmp_path / "test.sqlite3"),
        }
    )
    with app.test_client() as test_client:
        yield test_client


def _create_client(client):
    response = client.post(
        "/api/clients",
        json={"client_code": "DSO001", "name": "某连锁口腔集团", "credit_days": 30},
    )
    assert response.status_code == 201
    return response.get_json()["id"]


def test_monthly_settlement_flow(client):
    client_id = _create_client(client)

    order_payloads = [
        {
            "order_no": "SO-202603-001",
            "client_id": client_id,
            "order_date": "2026-03-03",
            "description": "种植体批量采购",
            "amount": "1000.00",
        },
        {
            "order_no": "SO-202603-002",
            "client_id": client_id,
            "order_date": "2026-03-18",
            "description": "正畸耗材",
            "amount": "2500.50",
        },
        {
            "order_no": "SO-202604-003",
            "client_id": client_id,
            "order_date": "2026-04-02",
            "description": "口扫配件",
            "amount": "800.00",
        },
    ]
    for payload in order_payloads:
        response = client.post("/api/orders", json=payload)
        assert response.status_code == 201

    invoice_response = client.post(
        "/api/invoices/generate",
        json={"client_id": client_id, "period": "2026-03"},
    )
    assert invoice_response.status_code == 200
    invoice_data = invoice_response.get_json()
    assert invoice_data["total_amount"] == "3500.50"
    assert invoice_data["status"] == "open"
    assert invoice_data["order_count"] == 2

    orders_response = client.get("/api/orders", query_string={"client_id": client_id})
    orders = {row["order_no"]: row for row in orders_response.get_json()}
    assert orders["SO-202603-001"]["status"] == "invoiced"
    assert orders["SO-202603-002"]["status"] == "invoiced"
    assert orders["SO-202604-003"]["status"] == "confirmed"

    summary_response = client.get("/api/receivables/summary")
    summary = summary_response.get_json()
    assert summary["open_amount"] == "3500.50"
    assert summary["overdue_amount"] in {"0.00", "3500.50"}

    mark_paid_response = client.post(
        f"/api/invoices/{invoice_data['id']}/mark-paid",
        json={"paid_at": "2026-05-20", "settlement_ref": "BankTransfer-20260520"},
    )
    assert mark_paid_response.status_code == 200
    assert mark_paid_response.get_json()["status"] == "paid"

    summary_after_paid = client.get("/api/receivables/summary").get_json()
    assert summary_after_paid["open_amount"] == "0.00"
    assert summary_after_paid["overdue_amount"] == "0.00"


def test_generate_invoice_without_orders(client):
    client_id = _create_client(client)
    response = client.post(
        "/api/invoices/generate",
        json={"client_id": client_id, "period": "2026-03"},
    )
    assert response.status_code == 400
    assert "没有可出账订单" in response.get_json()["error"]


def test_generate_invoice_same_period_twice(client):
    client_id = _create_client(client)
    client.post(
        "/api/orders",
        json={
            "order_no": "SO-202603-011",
            "client_id": client_id,
            "order_date": "2026-03-10",
            "description": "测试订单",
            "amount": "500.00",
        },
    )
    first = client.post(
        "/api/invoices/generate",
        json={"client_id": client_id, "period": "2026-03"},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/invoices/generate",
        json={"client_id": client_id, "period": "2026-03"},
    )
    assert second.status_code == 409
    assert "已经出账" in second.get_json()["error"]
