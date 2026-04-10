# DSO 月结订单系统

一个面向 DSO 大客户的轻量订单系统 MVP：

- 不接支付
- 适合总部统一采购、按月对账
- 支持客户建档、订单录入、月结对账单生成与状态跟进

## 功能范围

### 1. 客户管理

- 维护 DSO 客户主档
- 支持客户编号、联系人、账期说明、结算天数、备注

### 2. 订单管理

- 录入客户订单
- 支持商品/服务项目、数量、单价、下单日期、交付日期、状态
- 只有 `已交付` 且 `未出账` 的订单才可进入月结账单

### 3. 月结对账单

- 按 `客户 + 月份` 生成唯一对账单
- 自动汇总该月已交付且尚未入账的订单
- 对账单状态支持：
  - `待发送`
  - `已发送`
  - `已结清`

## 技术选型

- Python 3.12
- Flask
- SQLite
- pytest

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

启动后访问：

```text
http://127.0.0.1:5000
```

## 测试

```bash
python3 -m pytest
```

## 数据说明

- 默认使用 SQLite，数据库文件位于 `instance/dso.sqlite3`
- 首次启动会自动建表并写入少量演示数据
- 后续重启不会清空已有数据

## 目录结构

```text
.
├── app.py
├── requirements.txt
├── schema.sql
├── templates
│   ├── base.html
│   ├── customers.html
│   ├── dashboard.html
│   ├── orders.html
│   ├── statement_detail.html
│   └── statements.html
└── tests
    └── test_app.py
```
