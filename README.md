# DSO 月结订单系统

一个面向 DSO 大客户的轻量订单系统 MVP，聚焦以下业务场景：

- 不接支付网关，不做在线付款
- 支持 DSO / 连锁口腔等大客户月结
- 记录客户授信和账期天数
- 维护商品目录和订单明细
- 按账期归集已发货订单，生成月结算单
- 导出 CSV 给财务和客户对账

## 功能概览

### 1. 客户管理

- 维护 DSO 客户档案
- 配置客户编码、商务联系人、财务邮箱
- 设置账期天数和授信额度

### 2. 商品目录

- 维护 SKU、标准名称、单位和挂牌价
- 新建订单时可直接带入商品信息

### 3. 订单管理

- 创建订单并录入 PO、订单日期、发货日期、备注
- 管理订单状态：草稿 / 已确认 / 已发货
- 已发货订单可纳入月结流程

### 4. 月结算单

- 每个客户每个账期只有一张结算单
- 草稿态可持续追加当月新发货订单
- 发送后锁定内容，结清后自动关闭关联订单
- 支持 CSV 导出

## 技术栈

- Python 3.12
- Flask 3.1
- SQLite
- Jinja2 模板

## 快速启动

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

默认地址：

```text
http://127.0.0.1:5000
```

系统首次启动会自动创建 SQLite 数据库，并写入少量示例客户和商品，便于直接演示。

## 测试

```bash
python3 -m unittest discover -s tests
```

## 目录结构

```text
.
├── app.py
├── order_system
│   ├── __init__.py
│   ├── db.py
│   ├── services.py
│   └── templates
│       ├── base.html
│       ├── customers.html
│       ├── dashboard.html
│       ├── order_form.html
│       ├── orders.html
│       ├── products.html
│       ├── statement_detail.html
│       └── statements.html
└── tests
    └── test_app.py
```

## 适用场景

这个版本适合内部销售运营、客服或财务团队先把 DSO 大客户的下单和月结流程跑起来。如果后续要进一步产品化，可以继续扩展：

- 角色权限
- 审批流
- 发货单 / 出库单
- 合同价 / 客户专属价
- 发票管理
- ERP / CRM 对接
