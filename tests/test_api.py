import os
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure tests use a dedicated sqlite file.
DB_PATH = Path("test_dso_orders.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    if DB_PATH.exists():
        DB_PATH.unlink()


def test_dso_monthly_billing_flow():
    client = TestClient(app)
    headers = {}

    # 0) Protected endpoints should require login
    unauthorized_resp = client.get("/customers")
    assert unauthorized_resp.status_code == 401

    # 1) Register user and get bearer token
    register_resp = client.post(
        "/auth/register",
        json={
            "email": "ops.manager@example.com",
            "full_name": "Ops Manager",
            "password": "StrongPass123",
        },
    )
    assert register_resp.status_code == 200
    token = register_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2) Create customer (monthly billing only)
    customer_resp = client.post(
        "/customers",
        json={
            "name": "Acme DSO Group",
            "contact_email": "finance@acme-dso.com",
            "credit_terms_days": 30,
        },
        headers=headers,
    )
    assert customer_resp.status_code == 200
    customer = customer_resp.json()
    assert customer["billing_cycle"] == "monthly"

    # 3) Create product
    product_resp = client.post(
        "/products",
        json={"sku": "SKU-1001", "name": "Dental Aligners", "unit": "set", "unit_price": 88.5},
        headers=headers,
    )
    assert product_resp.status_code == 200
    product = product_resp.json()

    # 4) Create order
    order_resp = client.post(
        "/orders",
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "quantity": 3}],
        },
        headers=headers,
    )
    assert order_resp.status_code == 200
    order = order_resp.json()
    assert order["status"] == "draft"
    assert order["total_amount"] == 265.5

    # 5) Confirm order, then create logistics shipment record
    confirm_resp = client.post(f"/orders/{order['id']}/confirm", headers=headers)
    assert confirm_resp.status_code == 200
    shipment_resp = client.post(
        "/shipments",
        json={
            "order_id": order["id"],
            "carrier_name": "SF Express",
            "tracking_no": "SF-TRACK-0001",
            "remarks": "Main warehouse outbound",
        },
        headers=headers,
    )
    assert shipment_resp.status_code == 200
    shipment = shipment_resp.json()
    assert shipment["status"] == "shipped"
    assert shipment["tracking_no"] == "SF-TRACK-0001"

    # 6) List shipment records by order
    shipment_list_resp = client.get(f"/shipments?order_id={order['id']}", headers=headers)
    assert shipment_list_resp.status_code == 200
    shipments = shipment_list_resp.json()
    assert len(shipments) == 1
    assert shipments[0]["id"] == shipment["id"]

    # 7) Optional receiving confirmation
    receive_resp = client.post(f"/shipments/{shipment['id']}/receive", json={"received": True}, headers=headers)
    assert receive_resp.status_code == 200
    received_shipment = receive_resp.json()
    assert received_shipment["status"] == "received"

    # 8) Generate monthly invoice
    order_after_shipping = client.get("/orders", headers=headers).json()[0]
    billing_month = order_after_shipping["order_date"][:7]
    invoice_resp = client.post(f"/billing/monthly/{customer['id']}/{billing_month}", headers=headers)
    assert invoice_resp.status_code == 200
    invoice = invoice_resp.json()
    assert invoice["status"] == "issued"
    assert invoice["total_amount"] == 265.5

    # 9) Receivable report should include unsettled amount
    report_resp = client.get("/reports/receivables", headers=headers)
    assert report_resp.status_code == 200
    rows = report_resp.json()
    target = [row for row in rows if row["customer_id"] == customer["id"]][0]
    assert target["total_unsettled_amount"] == 265.5
    assert target["unsettled_invoices"] == 1

    # 10) Settle manually (no payment integration)
    settle_resp = client.post(
        f"/invoices/{invoice['id']}/settle",
        json={"settled": True},
        headers=headers,
    )
    assert settle_resp.status_code == 200
    settled_invoice = settle_resp.json()
    assert settled_invoice["status"] == "settled"

