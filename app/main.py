from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Customer, Invoice, Order, OrderItem, Product
from app.schemas import (
    CustomerCreate,
    CustomerOut,
    InvoiceOut,
    MarkInvoiceSettledIn,
    OrderCreate,
    OrderOut,
    ProductCreate,
    ProductOut,
    ReceivableSummaryOut,
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="DSO Monthly Settlement Order System",
    description="Order management for DSO enterprise customers with monthly billing and no online payment.",
    version="0.1.0",
    lifespan=lifespan,
)


def _gen_order_no(db: Session) -> str:
    count = db.query(func.count(Order.id)).scalar() or 0
    return f"SO{date.today().strftime('%Y%m%d')}{count + 1:04d}"


def _gen_invoice_no(db: Session) -> str:
    count = db.query(func.count(Invoice.id)).scalar() or 0
    return f"INV{date.today().strftime('%Y%m%d')}{count + 1:04d}"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/customers", response_model=CustomerOut)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)) -> Customer:
    existing = db.query(Customer).filter(Customer.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Customer name already exists")
    customer = Customer(
        name=payload.name,
        contact_email=payload.contact_email,
        credit_terms_days=payload.credit_terms_days,
        billing_cycle="monthly",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@app.get("/customers", response_model=List[CustomerOut])
def list_customers(db: Session = Depends(get_db)) -> List[Customer]:
    return db.query(Customer).order_by(Customer.id.desc()).all()


@app.post("/products", response_model=ProductOut)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    existing = db.query(Product).filter(Product.sku == payload.sku).first()
    if existing:
        raise HTTPException(status_code=409, detail="Product SKU already exists")
    product = Product(
        sku=payload.sku,
        name=payload.name,
        unit=payload.unit,
        unit_price=payload.unit_price,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get("/products", response_model=List[ProductOut])
def list_products(db: Session = Depends(get_db)) -> List[Product]:
    return db.query(Product).order_by(Product.id.desc()).all()


@app.post("/orders", response_model=OrderOut)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)) -> Order:
    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    order = Order(
        order_no=_gen_order_no(db),
        customer_id=payload.customer_id,
        status="draft",
        expected_ship_date=payload.expected_ship_date,
        notes=payload.notes,
    )
    db.add(order)
    db.flush()

    total = 0.0
    for item in payload.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        line_total = round(item.quantity * product.unit_price, 2)
        total += line_total
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.unit_price,
                line_total=line_total,
            )
        )

    order.total_amount = round(total, 2)
    db.commit()
    db.refresh(order)
    return order


@app.get("/orders", response_model=List[OrderOut])
def list_orders(db: Session = Depends(get_db)) -> List[Order]:
    return db.query(Order).order_by(Order.id.desc()).all()


@app.post("/orders/{order_id}/confirm", response_model=OrderOut)
def confirm_order(order_id: int, db: Session = Depends(get_db)) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft orders can be confirmed")
    order.status = "confirmed"
    db.commit()
    db.refresh(order)
    return order


@app.post("/orders/{order_id}/ship", response_model=OrderOut)
def ship_order(order_id: int, db: Session = Depends(get_db)) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "confirmed":
        raise HTTPException(status_code=400, detail="Only confirmed orders can be shipped")
    order.status = "shipped"
    db.commit()
    db.refresh(order)
    return order


@app.post("/billing/monthly/{customer_id}/{billing_month}", response_model=InvoiceOut)
def create_monthly_invoice(customer_id: int, billing_month: str, db: Session = Depends(get_db)) -> Invoice:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if len(billing_month) != 7 or billing_month[4] != "-":
        raise HTTPException(status_code=400, detail="billing_month must be in YYYY-MM format")

    existing_invoice = (
        db.query(Invoice)
        .filter(Invoice.customer_id == customer_id, Invoice.billing_month == billing_month)
        .first()
    )
    if existing_invoice:
        raise HTTPException(status_code=409, detail="Invoice already exists for this customer month")

    orders = (
        db.query(Order)
        .filter(
            Order.customer_id == customer_id,
            Order.status == "shipped",
            Order.invoice_id.is_(None),
            func.strftime("%Y-%m", Order.order_date) == billing_month,
        )
        .all()
    )
    if not orders:
        raise HTTPException(status_code=400, detail="No shipped uninvoiced orders in this billing month")

    total = round(sum(o.total_amount for o in orders), 2)
    issued_date = date.today()
    due_date = issued_date + timedelta(days=customer.credit_terms_days)
    invoice = Invoice(
        invoice_no=_gen_invoice_no(db),
        customer_id=customer_id,
        billing_month=billing_month,
        issued_date=issued_date,
        due_date=due_date,
        total_amount=total,
        status="issued",
    )
    db.add(invoice)
    db.flush()
    for order in orders:
        order.invoice_id = invoice.id
    db.commit()
    db.refresh(invoice)
    return invoice


@app.get("/invoices", response_model=List[InvoiceOut])
def list_invoices(
    customer_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> List[Invoice]:
    query = db.query(Invoice)
    if customer_id is not None:
        query = query.filter(Invoice.customer_id == customer_id)
    if status is not None:
        query = query.filter(Invoice.status == status)
    return query.order_by(Invoice.id.desc()).all()


@app.post("/invoices/{invoice_id}/settle", response_model=InvoiceOut)
def settle_invoice(
    invoice_id: int,
    payload: MarkInvoiceSettledIn,
    db: Session = Depends(get_db),
) -> Invoice:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if payload.settled:
        invoice.status = "settled"
        invoice.settled_at = func.now()
    else:
        invoice.status = "issued"
        invoice.settled_at = None
    db.commit()
    db.refresh(invoice)
    return invoice


@app.get("/reports/receivables", response_model=List[ReceivableSummaryOut])
def receivable_summary(db: Session = Depends(get_db)) -> List[ReceivableSummaryOut]:
    rows = (
        db.query(
            Customer.id.label("customer_id"),
            Customer.name.label("customer_name"),
            func.coalesce(func.sum(Invoice.total_amount), 0.0).label("total_unsettled_amount"),
            func.count(Invoice.id).label("unsettled_invoices"),
        )
        .join(Invoice, Invoice.customer_id == Customer.id, isouter=True)
        .filter((Invoice.status == "issued") | (Invoice.status.is_(None)))
        .group_by(Customer.id, Customer.name)
        .all()
    )

    return [
        ReceivableSummaryOut(
            customer_id=row.customer_id,
            customer_name=row.customer_name,
            total_unsettled_amount=float(row.total_unsettled_amount or 0.0),
            unsettled_invoices=int(row.unsettled_invoices or 0),
        )
        for row in rows
    ]
