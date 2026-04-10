# DSO 大客户月结订单系统

面向 DSO 大客户的月结订单管理系统，支持客户管理、产品管理、订单管理、月结对账等核心功能。无需对接支付系统，适合大客户月结场景。

## 功能模块

- **工作台** - 关键指标一览（客户数、订单数、本月营收、应收账款等）
- **客户管理** - 大客户信息维护，支持账期、信用额度设置
- **产品管理** - 产品信息及定价维护
- **订单管理** - 创建订单、状态流转（待确认 → 已确认 → 已发货 → 已完成）
- **月结账单** - 按月自动汇总生成账单，支持确认/标记付款/导出 Excel

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python, FastAPI, SQLAlchemy, SQLite |
| 前端 | React, TypeScript, Ant Design, Vite |
| 数据导出 | openpyxl (Excel) |

## 快速开始

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 启动前端（开发模式）

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 即可使用。

### 3. 生产部署

```bash
# 构建前端
cd frontend && npm run build

# 后端会自动 serve 前端静态文件
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000 即可。

## 订单状态流转

```
待确认(pending) → 已确认(confirmed) → 已发货(shipped) → 已完成(completed)
     ↓                  ↓
  已取消(cancelled)   已取消(cancelled)
```

## 月结流程

1. 正常创建并处理订单
2. 月末在「月结账单」页面点击「生成月结账单」，选择年月
3. 系统自动汇总该月所有已确认/已发货/已完成的订单
4. 确认账单后发送给客户对账
5. 客户付款后标记为「已付款」
6. 支持导出 Excel 明细给客户

## API 文档

启动后端后访问 http://localhost:8000/docs 查看 Swagger 文档。

## 金额说明

系统内部所有金额以「分」为单位存储，前端展示时自动转换为「元」，避免浮点精度问题。
