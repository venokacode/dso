from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List

import models
import schemas
import crud
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="DSO Order System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/api/dashboard", response_model=schemas.DashboardStats)
def dashboard(db: Session = Depends(get_db)):
    return crud.get_dashboard_stats(db)


# ── Customers ─────────────────────────────────────────────────────────────────

@app.get("/api/customers", response_model=List[schemas.CustomerOut])
def list_customers(
    skip: int = 0,
    limit: int = 200,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.get_customers(db, skip, limit, status, search)


@app.get("/api/customers/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    obj = crud.get_customer(db, customer_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    return obj


@app.post("/api/customers", response_model=schemas.CustomerOut, status_code=201)
def create_customer(data: schemas.CustomerCreate, db: Session = Depends(get_db)):
    return crud.create_customer(db, data)


@app.patch("/api/customers/{customer_id}", response_model=schemas.CustomerOut)
def update_customer(customer_id: int, data: schemas.CustomerUpdate, db: Session = Depends(get_db)):
    obj = crud.update_customer(db, customer_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    return obj


# ── Products ──────────────────────────────────────────────────────────────────

@app.get("/api/products", response_model=List[schemas.ProductOut])
def list_products(
    skip: int = 0,
    limit: int = 500,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.get_products(db, skip, limit, is_active, search)


@app.get("/api/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    obj = crud.get_product(db, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    return obj


@app.post("/api/products", response_model=schemas.ProductOut, status_code=201)
def create_product(data: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, data)


@app.patch("/api/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, data: schemas.ProductUpdate, db: Session = Depends(get_db)):
    obj = crud.update_product(db, product_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    return obj


# ── Orders ────────────────────────────────────────────────────────────────────

@app.get("/api/orders", response_model=List[schemas.OrderListOut])
def list_orders(
    skip: int = 0,
    limit: int = 200,
    customer_id: Optional[int] = None,
    status: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return crud.get_orders(db, skip, limit, customer_id, status, year, month)


@app.get("/api/orders/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    obj = crud.get_order(db, order_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Order not found")
    return obj


@app.post("/api/orders", response_model=schemas.OrderOut, status_code=201)
def create_order(data: schemas.OrderCreate, db: Session = Depends(get_db)):
    return crud.create_order(db, data)


@app.patch("/api/orders/{order_id}", response_model=schemas.OrderOut)
def update_order(order_id: int, data: schemas.OrderUpdate, db: Session = Depends(get_db)):
    obj = crud.update_order(db, order_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Order not found")
    return obj


@app.delete("/api/orders/{order_id}", status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    if not crud.delete_order(db, order_id):
        raise HTTPException(status_code=404, detail="Order not found")


# ── Monthly Statements ────────────────────────────────────────────────────────

@app.get("/api/statements", response_model=List[schemas.StatementListOut])
def list_statements(
    skip: int = 0,
    limit: int = 200,
    customer_id: Optional[int] = None,
    status: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return crud.get_statements(db, skip, limit, customer_id, status, year, month)


@app.get("/api/statements/{statement_id}", response_model=schemas.StatementOut)
def get_statement(statement_id: int, db: Session = Depends(get_db)):
    obj = crud.get_statement(db, statement_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Statement not found")
    return obj


@app.post("/api/statements", response_model=schemas.StatementOut, status_code=201)
def create_statement(data: schemas.StatementCreate, db: Session = Depends(get_db)):
    return crud.create_statement(db, data)


@app.patch("/api/statements/{statement_id}", response_model=schemas.StatementOut)
def update_statement(statement_id: int, data: schemas.StatementUpdate, db: Session = Depends(get_db)):
    obj = crud.update_statement(db, statement_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Statement not found")
    return obj


# ── Seed demo data ────────────────────────────────────────────────────────────

@app.post("/api/seed", status_code=201)
def seed_demo_data(db: Session = Depends(get_db)):
    from datetime import date
    from decimal import Decimal

    if db.query(models.Customer).count() > 0:
        return {"message": "Already seeded"}

    customers = [
        models.Customer(code="DSO001", name="北京大顺通科技有限公司", contact_person="张经理",
                        email="zhang@dso001.com", phone="010-12345678",
                        credit_limit=Decimal("500000"), payment_terms_days=30),
        models.Customer(code="DSO002", name="上海大顺通贸易有限公司", contact_person="李总",
                        email="li@dso002.com", phone="021-87654321",
                        credit_limit=Decimal("800000"), payment_terms_days=45),
        models.Customer(code="DSO003", name="广州大顺通实业有限公司", contact_person="王主任",
                        email="wang@dso003.com", phone="020-11223344",
                        credit_limit=Decimal("300000"), payment_terms_days=30),
    ]
    for c in customers:
        db.add(c)

    products = [
        models.Product(sku="PRD001", name="工业润滑油 5L", unit="桶", unit_price=Decimal("288.00")),
        models.Product(sku="PRD002", name="防锈喷剂 500ml", unit="瓶", unit_price=Decimal("45.00")),
        models.Product(sku="PRD003", name="清洁剂套装", unit="套", unit_price=Decimal("120.00")),
        models.Product(sku="PRD004", name="密封胶 300ml", unit="支", unit_price=Decimal("38.00")),
        models.Product(sku="PRD005", name="螺丝刀套装 32件", unit="套", unit_price=Decimal("156.00")),
    ]
    for p in products:
        db.add(p)

    db.commit()
    return {"message": "Demo data seeded successfully"}
