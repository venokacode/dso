# DSO 大客户月结订单系统

无需支付集成的 B2B 订单管理系统，专为 DSO 大客户月结场景设计。

## 功能特性

- **客户管理** - 大客户信息维护，支持信用额度、账期设置
- **产品管理** - 产品目录管理，含 SKU、单价、单位
- **订单管理** - 完整订单生命周期（草稿→确认→发货→签收），支持取消
- **月结对账** - 按月自动汇总订单，生成对账单，跟踪付款状态

## 技术栈

- **后端**: FastAPI + SQLAlchemy 2.0
- **数据库**: SQLite（可切换 PostgreSQL/MySQL）
- **迁移**: Alembic
- **测试**: pytest

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload

# 访问 API 文档
open http://localhost:8000/docs
```

## 运行测试

```bash
pytest tests/ -v
```

## API 概览

所有接口均以 `/api/v1` 为前缀。

### 客户管理 `/api/v1/customers`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/customers` | 创建客户 |
| GET | `/customers` | 客户列表（支持分页、搜索） |
| GET | `/customers/{id}` | 客户详情 |
| PUT | `/customers/{id}` | 更新客户 |
| DELETE | `/customers/{id}` | 删除客户 |

### 产品管理 `/api/v1/products`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/products` | 创建产品 |
| GET | `/products` | 产品列表（支持分页、搜索） |
| GET | `/products/{id}` | 产品详情 |
| PUT | `/products/{id}` | 更新产品 |
| DELETE | `/products/{id}` | 删除产品 |

### 订单管理 `/api/v1/orders`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/orders` | 创建订单 |
| GET | `/orders` | 订单列表（支持按客户、状态、月份筛选） |
| GET | `/orders/{id}` | 订单详情 |
| PUT | `/orders/{id}` | 更新订单（仅草稿） |
| PATCH | `/orders/{id}/status` | 更新订单状态 |
| DELETE | `/orders/{id}` | 删除订单（仅草稿） |

### 月结对账 `/api/v1/statements`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/statements` | 生成月结对账单 |
| GET | `/statements` | 对账单列表 |
| GET | `/statements/{id}` | 对账单详情（含关联订单） |
| PATCH | `/statements/{id}/status` | 更新对账单状态 |

## 数据模型

### 金额说明

所有金额字段以 **分** 为单位存储（整数），避免浮点精度问题。例如 `unit_price: 9900` 表示 99.00 元。

### 订单状态流转

```
draft → confirmed → shipped → delivered
  ↓        ↓
cancelled cancelled
```

### 对账单状态流转

```
pending → sent → confirmed → paid
                     ↓
                  overdue → paid
```

## 配置

通过环境变量或 `.env` 文件配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///./dso_orders.db` | 数据库连接 |
| `APP_NAME` | `DSO 大客户月结订单系统` | 应用名称 |
