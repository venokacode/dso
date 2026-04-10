# DSO 大客户订单系统

面向 DSO 大客户的月结订单管理系统，无需对接支付，支持月结账期管理。

## 功能模块

| 模块 | 功能 |
|------|------|
| 仪表盘 | 本月订单量/金额概览、待处理账单、逾期预警 |
| 客户管理 | 大客户档案、授信额度、账期天数 |
| 产品管理 | 产品目录、SKU、单价管理 |
| 订单管理 | 创建/查看/状态变更、行级折扣、整单折扣 |
| 月结账单 | 按客户+月份自动汇总订单、状态流转、到期日管理 |

## 订单状态流转

```
草稿 → 已确认 → 已发货 → 已收货
           ↘ 已取消
```

## 账单状态流转

```
待出账 → 已出账 → 已结清
              ↘ 已逾期 → 已结清
```

## 技术栈

- **后端**: Python 3 + FastAPI + SQLAlchemy + SQLite
- **前端**: React 18 + TypeScript + Vite + TanStack Query

## 快速启动

### 方式一：一键启动

```bash
bash start.sh
```

### 方式二：分别启动

**后端**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**前端**

```bash
cd frontend
npm install
npm run dev
```

访问地址：
- 前端页面：http://localhost:5173
- 后端 API 文档：http://localhost:8000/docs

## 初始化演示数据

进入「仪表盘」页面，点击右上角「初始化演示数据」按钮，
系统将自动创建 3 个示例客户和 5 个示例产品。

## API 说明

| 端点 | 说明 |
|------|------|
| `GET /api/dashboard` | 仪表盘统计数据 |
| `GET/POST /api/customers` | 客户列表/创建 |
| `PATCH /api/customers/{id}` | 更新客户 |
| `GET/POST /api/products` | 产品列表/创建 |
| `PATCH /api/products/{id}` | 更新产品 |
| `GET/POST /api/orders` | 订单列表/创建 |
| `GET /api/orders/{id}` | 订单详情 |
| `PATCH /api/orders/{id}` | 更新订单（含状态变更） |
| `DELETE /api/orders/{id}` | 删除草稿订单 |
| `GET/POST /api/statements` | 账单列表/生成 |
| `GET /api/statements/{id}` | 账单详情 |
| `PATCH /api/statements/{id}` | 更新账单状态 |
| `POST /api/seed` | 初始化演示数据 |

数据存储在 `backend/dso_orders.db`（SQLite 文件）。
