# DSO Monthly Settlement Order System

一个面向 DSO 大客户的订单系统（不接在线支付），支持月结开票与应收管理。

## 功能范围

- 客户管理（固定月结账期）
- 商品管理
- 订单流转：`draft -> confirmed -> shipped`
- 月结开票：按客户 + 月份汇总已发货未开票订单
- 发票结清：人工标记结清（不做支付接口）
- 应收报表：按客户汇总未结清金额

## 技术栈

- FastAPI
- SQLAlchemy
- SQLite（默认本地文件 `dso_orders.db`）

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

访问文档：

- Swagger UI: `http://127.0.0.1:8000/docs`

## 核心接口

- `POST /customers` 创建客户
- `GET /customers` 客户列表
- `POST /products` 创建商品
- `GET /products` 商品列表
- `POST /orders` 创建订单（草稿）
- `GET /orders` 订单列表
- `POST /orders/{order_id}/confirm` 确认订单
- `POST /orders/{order_id}/ship` 发货
- `POST /billing/monthly/{customer_id}/{billing_month}` 月结开票（`YYYY-MM`）
- `GET /invoices` 发票列表
- `POST /invoices/{invoice_id}/settle` 人工标记结清
- `GET /reports/receivables` 应收汇总

## 业务说明（DSO 月结）

1. 订单先创建并确认，再发货。
2. 月末按客户和月份开票，自动汇总该月**已发货且未开票**订单。
3. 发票到期日 = 开票日 + 客户账期（默认 30 天）。
4. 系统不处理支付，只支持财务人工标记“已结清”。

## 运行测试

```bash
pytest -q
```
