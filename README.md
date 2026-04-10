# DSO Monthly Settlement Order System

An order management backend for DSO enterprise customers with monthly settlement.
Online payment is intentionally out of scope.

## Features

- User authentication (register, login, current user)
- Customer management (monthly billing cycle)
- Product management
- Order workflow: `draft -> confirmed -> shipped`
- Monthly invoicing: aggregate shipped, uninvoiced orders by customer + month
- Manual invoice settlement (no payment gateway)
- Accounts receivable summary by customer

## Tech Stack

- FastAPI
- SQLAlchemy
- SQLite (default local file: `dso_orders.db`)

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload
```

API docs:

- Swagger UI: `http://127.0.0.1:8000/docs`

## Authentication

Register and get token:

- `POST /auth/register`

Login and get token:

- `POST /auth/login`

Current user:

- `GET /auth/me`

Use the token in all business endpoints:

```text
Authorization: Bearer <access_token>
```

## Core Endpoints

- `POST /customers`
- `GET /customers`
- `POST /products`
- `GET /products`
- `POST /orders`
- `GET /orders`
- `POST /orders/{order_id}/confirm`
- `POST /orders/{order_id}/ship`
- `POST /billing/monthly/{customer_id}/{billing_month}` (`YYYY-MM`)
- `GET /invoices`
- `POST /invoices/{invoice_id}/settle`
- `GET /reports/receivables`

## DSO Monthly Settlement Rules

1. Create order, then confirm, then ship.
2. Generate monthly invoice from shipped and uninvoiced orders in that month.
3. Due date = issue date + customer credit term days (default: 30).
4. Payment processing is not included; finance team marks invoice as settled manually.

## Run Tests

```bash
python3 -m pytest -q
```
