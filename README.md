# dso

面向大客户（DSO）的**月结订单服务**：下单、状态流转、按自然月汇总对账；**不接支付**，账单由财务线下结算。

## 运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

默认 SQLite 路径：`data/orders.db`（首次启动自动建表）。可通过环境变量覆盖：

```bash
export DSO_DATABASE_URL="sqlite:////absolute/path/to/orders.db"
```

## API 摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/customers` | 创建大客户（`billing_cycle` 默认 `monthly`） |
| GET | `/customers` | 客户列表 |
| GET | `/customers/{id}` | 客户详情 |
| POST | `/orders` | 创建订单（行项目含 sku、数量、单价） |
| GET | `/orders` | 订单列表，可筛 `customer_id`、`status` |
| GET | `/orders/{id}` | 订单详情（含行小计与合计） |
| PATCH | `/orders/{id}/status` | 更新状态：`draft` → `submitted` → `confirmed` → `fulfilled`，或 `cancelled` |
| GET | `/statements/monthly` | 月结对账：`customer_id`、`year`、`month`（排除 `cancelled`） |

交互文档：启动后打开 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)。

## 测试

```bash
pytest
```
