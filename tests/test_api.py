import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite:///./test_dso_orders.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


class TestRoot:
    def test_root(self):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert data["version"] == "1.0.0"

    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestCustomers:
    def _create_customer(self, code="C001", name="测试客户"):
        return client.post("/api/v1/customers", json={
            "name": name,
            "code": code,
            "contact_person": "张三",
            "contact_phone": "13800138000",
            "payment_terms_days": 30,
            "credit_limit": 10000000,
        })

    def test_create_customer(self):
        resp = self._create_customer()
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "C001"
        assert data["name"] == "测试客户"
        assert data["status"] == "active"

    def test_create_duplicate_customer(self):
        self._create_customer()
        resp = self._create_customer()
        assert resp.status_code == 409

    def test_list_customers(self):
        self._create_customer("C001", "客户A")
        self._create_customer("C002", "客户B")
        resp = client.get("/api/v1/customers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_customers_with_keyword(self):
        self._create_customer("C001", "华为科技")
        self._create_customer("C002", "腾讯科技")
        resp = client.get("/api/v1/customers?keyword=华为")
        data = resp.json()
        assert data["total"] == 1

    def test_get_customer(self):
        create_resp = self._create_customer()
        cid = create_resp.json()["id"]
        resp = client.get(f"/api/v1/customers/{cid}")
        assert resp.status_code == 200

    def test_get_customer_not_found(self):
        resp = client.get("/api/v1/customers/9999")
        assert resp.status_code == 404

    def test_update_customer(self):
        create_resp = self._create_customer()
        cid = create_resp.json()["id"]
        resp = client.put(f"/api/v1/customers/{cid}", json={"name": "更新后的客户"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "更新后的客户"

    def test_delete_customer(self):
        create_resp = self._create_customer()
        cid = create_resp.json()["id"]
        resp = client.delete(f"/api/v1/customers/{cid}")
        assert resp.status_code == 204


class TestProducts:
    def _create_product(self, code="P001", name="测试产品"):
        return client.post("/api/v1/products", json={
            "name": name,
            "code": code,
            "unit": "件",
            "unit_price": 9900,
        })

    def test_create_product(self):
        resp = self._create_product()
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "P001"
        assert data["unit_price"] == 9900

    def test_create_duplicate_product(self):
        self._create_product()
        resp = self._create_product()
        assert resp.status_code == 409

    def test_list_products(self):
        self._create_product("P001")
        self._create_product("P002")
        resp = client.get("/api/v1/products")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_update_product(self):
        create_resp = self._create_product()
        pid = create_resp.json()["id"]
        resp = client.put(f"/api/v1/products/{pid}", json={"unit_price": 19900})
        assert resp.status_code == 200
        assert resp.json()["unit_price"] == 19900

    def test_delete_product(self):
        create_resp = self._create_product()
        pid = create_resp.json()["id"]
        resp = client.delete(f"/api/v1/products/{pid}")
        assert resp.status_code == 204


class TestOrders:
    def _setup_customer_and_product(self):
        c = client.post("/api/v1/customers", json={
            "name": "订单测试客户", "code": "OC001",
            "payment_terms_days": 30,
        })
        p = client.post("/api/v1/products", json={
            "name": "订单测试产品", "code": "OP001",
            "unit_price": 5000,
        })
        return c.json()["id"], p.json()["id"]

    def test_create_order(self):
        cid, pid = self._setup_customer_and_product()
        resp = client.post("/api/v1/orders", json={
            "customer_id": cid,
            "items": [{"product_id": pid, "quantity": 3}],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_amount"] == 15000
        assert len(data["items"]) == 1
        assert data["items"][0]["subtotal"] == 15000
        assert data["status"] == "draft"

    def test_create_order_invalid_customer(self):
        resp = client.post("/api/v1/orders", json={
            "customer_id": 9999,
            "items": [{"product_id": 1, "quantity": 1}],
        })
        assert resp.status_code == 404

    def test_order_status_transitions(self):
        cid, pid = self._setup_customer_and_product()
        order_resp = client.post("/api/v1/orders", json={
            "customer_id": cid,
            "items": [{"product_id": pid, "quantity": 1}],
        })
        oid = order_resp.json()["id"]

        resp = client.patch(f"/api/v1/orders/{oid}/status", json={"status": "confirmed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

        resp = client.patch(f"/api/v1/orders/{oid}/status", json={"status": "shipped"})
        assert resp.status_code == 200

        resp = client.patch(f"/api/v1/orders/{oid}/status", json={"status": "delivered"})
        assert resp.status_code == 200

    def test_invalid_status_transition(self):
        cid, pid = self._setup_customer_and_product()
        order_resp = client.post("/api/v1/orders", json={
            "customer_id": cid,
            "items": [{"product_id": pid, "quantity": 1}],
        })
        oid = order_resp.json()["id"]

        resp = client.patch(f"/api/v1/orders/{oid}/status", json={"status": "delivered"})
        assert resp.status_code == 400

    def test_cancel_order(self):
        cid, pid = self._setup_customer_and_product()
        order_resp = client.post("/api/v1/orders", json={
            "customer_id": cid,
            "items": [{"product_id": pid, "quantity": 1}],
        })
        oid = order_resp.json()["id"]

        resp = client.patch(f"/api/v1/orders/{oid}/status", json={"status": "cancelled"})
        assert resp.status_code == 200

    def test_delete_draft_order(self):
        cid, pid = self._setup_customer_and_product()
        order_resp = client.post("/api/v1/orders", json={
            "customer_id": cid,
            "items": [{"product_id": pid, "quantity": 1}],
        })
        oid = order_resp.json()["id"]
        resp = client.delete(f"/api/v1/orders/{oid}")
        assert resp.status_code == 204

    def test_cannot_delete_confirmed_order(self):
        cid, pid = self._setup_customer_and_product()
        order_resp = client.post("/api/v1/orders", json={
            "customer_id": cid,
            "items": [{"product_id": pid, "quantity": 1}],
        })
        oid = order_resp.json()["id"]
        client.patch(f"/api/v1/orders/{oid}/status", json={"status": "confirmed"})
        resp = client.delete(f"/api/v1/orders/{oid}")
        assert resp.status_code == 400

    def test_list_orders(self):
        cid, pid = self._setup_customer_and_product()
        client.post("/api/v1/orders", json={
            "customer_id": cid,
            "items": [{"product_id": pid, "quantity": 1}],
        })
        resp = client.get("/api/v1/orders")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_orders_by_customer(self):
        cid, pid = self._setup_customer_and_product()
        client.post("/api/v1/orders", json={
            "customer_id": cid,
            "items": [{"product_id": pid, "quantity": 1}],
        })
        resp = client.get(f"/api/v1/orders?customer_id={cid}")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


class TestStatements:
    def _setup_and_create_order(self):
        c = client.post("/api/v1/customers", json={
            "name": "对账测试客户", "code": "SC001",
            "payment_terms_days": 30,
        })
        p = client.post("/api/v1/products", json={
            "name": "对账测试产品", "code": "SP001",
            "unit_price": 10000,
        })
        cid, pid = c.json()["id"], p.json()["id"]

        order_resp = client.post("/api/v1/orders", json={
            "customer_id": cid,
            "items": [{"product_id": pid, "quantity": 5}],
        })
        oid = order_resp.json()["id"]
        month = order_resp.json()["statement_month"]

        client.patch(f"/api/v1/orders/{oid}/status", json={"status": "confirmed"})
        return cid, month

    def test_generate_statement(self):
        cid, month = self._setup_and_create_order()
        resp = client.post("/api/v1/statements", json={
            "customer_id": cid,
            "month": month,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_amount"] == 50000
        assert data["order_count"] == 1
        assert data["status"] == "pending"

    def test_duplicate_statement(self):
        cid, month = self._setup_and_create_order()
        client.post("/api/v1/statements", json={
            "customer_id": cid, "month": month,
        })
        resp = client.post("/api/v1/statements", json={
            "customer_id": cid, "month": month,
        })
        assert resp.status_code == 409

    def test_statement_status_flow(self):
        cid, month = self._setup_and_create_order()
        stmt_resp = client.post("/api/v1/statements", json={
            "customer_id": cid, "month": month,
        })
        sid = stmt_resp.json()["id"]

        resp = client.patch(f"/api/v1/statements/{sid}/status", json={"status": "sent"})
        assert resp.status_code == 200

        resp = client.patch(f"/api/v1/statements/{sid}/status", json={"status": "confirmed"})
        assert resp.status_code == 200

        resp = client.patch(f"/api/v1/statements/{sid}/status", json={"status": "paid"})
        assert resp.status_code == 200
        assert resp.json()["paid_at"] is not None

    def test_get_statement_detail(self):
        cid, month = self._setup_and_create_order()
        stmt_resp = client.post("/api/v1/statements", json={
            "customer_id": cid, "month": month,
        })
        sid = stmt_resp.json()["id"]

        resp = client.get(f"/api/v1/statements/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["orders"]) == 1

    def test_list_statements(self):
        cid, month = self._setup_and_create_order()
        client.post("/api/v1/statements", json={
            "customer_id": cid, "month": month,
        })
        resp = client.get("/api/v1/statements")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1
