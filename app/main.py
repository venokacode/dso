from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import List

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import generate_access_token, hash_password, token_expiry, utc_now, verify_password
from app.database import Base, engine, get_db
from app.models import Customer, Invoice, Order, OrderItem, Product, User, UserSession
from app.schemas import (
    AuthTokenOut,
    CustomerCreate,
    CustomerOut,
    InvoiceOut,
    MarkInvoiceSettledIn,
    OrderCreate,
    OrderOut,
    ProductCreate,
    ProductOut,
    ReceivableSummaryOut,
    UserLogin,
    UserOut,
    UserRegister,
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="DSO Monthly Settlement Order System",
    description="Order management for DSO enterprise customers with monthly billing, user authentication, and no online payment.",
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


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    session = db.query(UserSession).filter(UserSession.access_token == token).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid token")
    if session.expires_at < utc_now():
        raise HTTPException(status_code=401, detail="Token expired")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive")
    return user


def build_auth_response(user: User, db: Session) -> AuthTokenOut:
    token = generate_access_token()
    expires_at = token_expiry(hours=24)
    session = UserSession(user_id=user.id, access_token=token, expires_at=expires_at)
    db.add(session)
    db.commit()
    db.refresh(user)
    return AuthTokenOut(access_token=token, expires_at=expires_at, user=user)


@app.post("/auth/register", response_model=AuthTokenOut)
def register_user(payload: UserRegister, db: Session = Depends(get_db)) -> AuthTokenOut:
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return build_auth_response(user, db)


@app.post("/auth/login", response_model=AuthTokenOut)
def login_user(payload: UserLogin, db: Session = Depends(get_db)) -> AuthTokenOut:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive")
    return build_auth_response(user, db)


@app.get("/auth/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@app.post("/customers", response_model=CustomerOut)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Customer:
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
def list_customers(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> List[Customer]:
    return db.query(Customer).order_by(Customer.id.desc()).all()


@app.post("/products", response_model=ProductOut)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Product:
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
def list_products(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> List[Product]:
    return db.query(Product).order_by(Product.id.desc()).all()


@app.post("/orders", response_model=OrderOut)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Order:
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
def list_orders(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> List[Order]:
    return db.query(Order).order_by(Order.id.desc()).all()


@app.post("/orders/{order_id}/confirm", response_model=OrderOut)
def confirm_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Order:
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
def ship_order(order_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Order:
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
def create_monthly_invoice(
    customer_id: int,
    billing_month: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Invoice:
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
    _: User = Depends(get_current_user),
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
    _: User = Depends(get_current_user),
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
def receivable_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> List[ReceivableSummaryOut]:
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
