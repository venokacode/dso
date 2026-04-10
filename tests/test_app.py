from pathlib import Path

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path: Path):
    database_path = tmp_path / "test.sqlite3"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(database_path),
            "SEED_DEMO_DATA": False,
        }
    )
    return app.test_client()


def test_dashboard_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "DSO 月结订单系统".encode("utf-8") in response.data


def test_create_customer_and_order_then_generate_statement(client):
    customer_response = client.post(
        "/customers",
        data={
            "name": "测试口腔集团",
            "customer_code": "DSO-T001",
            "contact_name": "陈晨",
            "contact_email": "chenchen@example.com",
            "credit_terms": "月结 30 天",
            "billing_day": "30",
            "notes": "总部月结",
        },
        follow_redirects=True,
    )
    assert customer_response.status_code == 200
    assert "客户已创建".encode("utf-8") in customer_response.data

    orders_page = client.get("/orders")
    assert orders_page.status_code == 200
    assert "DSO-T001".encode("utf-8") in orders_page.data

    order_response = client.post(
        "/orders",
        data={
            "customer_id": "1",
            "item_name": "数字化导板服务",
            "quantity": "3",
            "unit_price": "5000",
            "order_date": "2026-04-03",
            "delivery_date": "2026-04-10",
            "status": "delivered",
            "remarks": "按门店拆分交付",
        },
        follow_redirects=True,
    )
    assert order_response.status_code == 200
    assert "订单已录入".encode("utf-8") in order_response.data

    statement_response = client.post(
        "/statements",
        data={
            "customer_id": "1",
            "billing_month": "2026-04",
        },
        follow_redirects=True,
    )
    assert statement_response.status_code == 200
    assert "月结对账单已生成".encode("utf-8") in statement_response.data
    assert "15,000.00".encode("utf-8") in statement_response.data


def test_delivered_order_requires_delivery_date(client):
    client.post(
        "/customers",
        data={
            "name": "校验客户",
            "customer_code": "DSO-T002",
            "billing_day": "30",
        },
        follow_redirects=True,
    )

    response = client.post(
        "/orders",
        data={
            "customer_id": "1",
            "item_name": "校验订单",
            "quantity": "1",
            "unit_price": "100",
            "order_date": "2026-04-11",
            "delivery_date": "",
            "status": "delivered",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "已交付订单必须填写交付日期".encode("utf-8") in response.data
