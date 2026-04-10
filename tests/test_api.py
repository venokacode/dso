def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


from decimal import Decimal


def test_customer_and_order_flow(client):
    r = client.post(
        "/customers",
        json={
            "code": "VIP-001",
            "name": "大客户 A",
            "billing_cycle": "monthly",
            "contact_email": "a@example.com",
        },
    )
    assert r.status_code == 201
    cid = r.json()["id"]

    r = client.post(
        "/orders",
        json={
            "customer_id": cid,
            "external_ref": "PO-2026-01",
            "lines": [
                {"sku": "SKU-1", "description": "产品甲", "quantity": "10", "unit_price": "100.00"},
            ],
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "draft"
    assert Decimal(data["subtotal"]) == Decimal("1000")
    oid = data["id"]

    r = client.patch(f"/orders/{oid}/status", json={"status": "confirmed"})
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    from datetime import date

    y, m = date.today().year, date.today().month
    r = client.get(f"/statements/monthly?customer_id={cid}&year={y}&month={m}")
    assert r.status_code == 200
    stmt = r.json()
    assert stmt["order_count"] == 1
    assert Decimal(stmt["total_amount"]) == Decimal("1000")
