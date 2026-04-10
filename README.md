# DSO 订单系统（无支付，月结）

这是一个面向 DSO 大客户的订单系统基础版：

- 不接在线支付网关
- 订单走月结（按客户 + 月份汇总应收）
- 提供客户、商品、订单、月结对账 API

## 1. 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

服务默认启动在 `http://127.0.0.1:8000`，文档地址：

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## 2. 数据模型（核心）

- **Customer（客户）**：大客户信息、结算日（`billing_cycle_day`）
- **Product（商品）**：SKU、单价
- **Order（订单）**：客户、日期、状态、金额
- **OrderItem（订单明细）**：商品快照、单价、数量、小计

订单状态：

- `CONFIRMED` / `INVOICED`：会计入当月应收
- `SETTLED` / `CANCELLED`：不计入应收

## 3. 关键接口

### 健康检查

`GET /health`

### 客户

- `POST /customers` 新建客户
- `GET /customers` 客户列表

示例：

```json
{
  "code": "DSO-ACME",
  "name": "Acme Hospital Group",
  "billing_cycle_day": 25
}
```

### 商品

- `POST /products` 新建商品
- `GET /products` 商品列表

### 订单

- `POST /orders` 创建订单（默认 `CONFIRMED`）
- `GET /orders/{order_id}` 查询订单详情
- `GET /orders?customer_id=1&month=2026-04` 订单列表过滤
- `PATCH /orders/{order_id}/status` 更新状态

创建订单示例：

```json
{
  "customer_id": 1,
  "order_date": "2026-04-08",
  "items": [
    { "product_id": 1, "quantity": 3 }
  ],
  "note": "DSO monthly purchase"
}
```

### 月结对账

- `GET /settlements/monthly?customer_id=1&month=2026-04`

返回当月应收汇总：

- `total_due`：应收总额
- `order_count`：纳入结算的订单数
- `due_date`：下月账期日（按客户 `billing_cycle_day` 计算）

## 4. 测试

```bash
pytest -q
```

已包含端到端测试：客户 -> 商品 -> 下单 -> 月结 -> 订单结清 -> 月结更新。
