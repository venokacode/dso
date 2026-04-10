# DSO 大客户订单系统（无支付，月结）

一个面向 DSO 大客户的轻量订单系统，核心目标：

- 不接在线支付网关
- 订单按月汇总出账（月结）
- 财务可手工核销回款
- 可查看当前应收与逾期风险

## 功能范围

- 客户管理（大客户档案、账期）
- 订单录入（订单金额、订单日期、客户归属）
- 月结出账（按客户 + 结算月生成账单）
- 回款核销（手工标记 invoice 已结清）
- 应收汇总（总应收、逾期应收、按客户拆分）

## 技术栈

- Python 3.12+
- Flask
- SQLite
- pytest

## 快速启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 run.py
```

服务默认启动在 `http://127.0.0.1:8000`。

## 关键 API

### 1) 新建客户

`POST /api/clients`

```json
{
  "client_code": "DSO001",
  "name": "某连锁口腔集团",
  "credit_days": 30
}
```

### 2) 录入订单

`POST /api/orders`

```json
{
  "order_no": "SO-202603-001",
  "client_id": 1,
  "order_date": "2026-03-18",
  "description": "正畸耗材",
  "amount": "2500.50"
}
```

### 3) 生成月结账单

`POST /api/invoices/generate`

```json
{
  "client_id": 1,
  "period": "2026-03"
}
```

说明：

- 只汇总该客户在该月份中 `confirmed` 状态且未出账的订单
- 每个客户每个结算月只允许 1 张账单
- 默认开票日为次月 1 号，到期日 = 开票日 + `credit_days`

### 4) 核销回款（手工）

`POST /api/invoices/{invoice_id}/mark-paid`

```json
{
  "paid_at": "2026-05-20",
  "settlement_ref": "BankTransfer-20260520"
}
```

### 5) 应收看板

`GET /api/receivables/summary`

返回：

- `open_amount`: 当前未结清应收总额
- `overdue_amount`: 已逾期未结清应收总额
- `client_breakdown`: 各客户应收拆分

## 测试

```bash
pytest -q
```
