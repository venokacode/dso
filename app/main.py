from __future__ import annotations

import calendar
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session, selectinload

from .database import Base, build_engine, build_session_factory, resolve_db_url
from .models import Customer, CustomerStatus, Order, OrderItem, OrderStatus, Product
from .schemas import (
    CustomerCreate,
    CustomerRead,
    MonthlySettlementItem,
    MonthlySettlementRead,
    OrderCreate,
    OrderRead,
    OrderStatusUpdate,
    ProductCreate,
    ProductRead,
)


def _month_bounds(month: str) -> tuple[date, date]:
    try:
        first_day = datetime.strptime(month, "%Y-%m").date().replace(day=1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="month must be in YYYY-MM format") from exc

    if first_day.month == 12:
        next_month = date(first_day.year + 1, 1, 1)
    else:
        next_month = date(first_day.year, first_day.month + 1, 1)
    return first_day, next_month


def _month_due_date(statement_month: str, billing_cycle_day: int) -> date:
    first_day, _ = _month_bounds(statement_month)
    if first_day.month == 12:
        due_year, due_month = first_day.year + 1, 1
    else:
        due_year, due_month = first_day.year, first_day.month + 1
    last_day = calendar.monthrange(due_year, due_month)[1]
    return date(due_year, due_month, min(billing_cycle_day, last_day))


def _generate_order_no(order_date: date) -> str:
    short_id = uuid4().hex[:8].upper()
    return f"SO-{order_date.strftime('%Y%m%d')}-{short_id}"


def _get_db(request: Request):
    db = request.app.state.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_app(db_url: str | None = None) -> FastAPI:
    engine = build_engine(resolve_db_url(db_url))
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(bind=engine)
        app.state.SessionLocal = session_factory
        yield

    app = FastAPI(
        title="DSO Order System",
        description="Order management for key account customers with monthly settlement and no online payment.",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/customers", response_model=CustomerRead, status_code=201)
    def create_customer(payload: CustomerCreate, db: Session = Depends(_get_db)):
        existing = db.scalar(select(Customer).where(Customer.code == payload.code))
        if existing:
            raise HTTPException(status_code=409, detail="Customer code already exists")

        customer = Customer(
            code=payload.code,
            name=payload.name,
            billing_cycle_day=payload.billing_cycle_day,
            status=CustomerStatus.ACTIVE,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer

    @app.get("/customers", response_model=list[CustomerRead])
    def list_customers(db: Session = Depends(_get_db)):
        return db.scalars(select(Customer).order_by(Customer.id.desc())).all()

    @app.post("/products", response_model=ProductRead, status_code=201)
    def create_product(payload: ProductCreate, db: Session = Depends(_get_db)):
        existing = db.scalar(select(Product).where(Product.sku == payload.sku))
        if existing:
            raise HTTPException(status_code=409, detail="SKU already exists")
        product = Product(sku=payload.sku, name=payload.name, unit_price=payload.unit_price, active=True)
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    @app.get("/products", response_model=list[ProductRead])
    def list_products(db: Session = Depends(_get_db)):
        return db.scalars(select(Product).where(Product.active.is_(True)).order_by(Product.id.desc())).all()

    @app.post("/orders", response_model=OrderRead, status_code=201)
    def create_order(payload: OrderCreate, db: Session = Depends(_get_db)):
        customer = db.get(Customer, payload.customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        if customer.status != CustomerStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Customer is inactive")

        product_ids = [item.product_id for item in payload.items]
        products = db.scalars(select(Product).where(Product.id.in_(product_ids))).all()
        products_map = {product.id: product for product in products}

        missing = [product_id for product_id in product_ids if product_id not in products_map]
        if missing:
            raise HTTPException(status_code=404, detail=f"Products not found: {missing}")

        order_items: list[OrderItem] = []
        subtotal = Decimal("0.00")
        for item in payload.items:
            product = products_map[item.product_id]
            if not product.active:
                raise HTTPException(status_code=400, detail=f"Product {product.id} is inactive")
            line_total = Decimal(product.unit_price) * item.quantity
            subtotal += line_total
            order_items.append(
                OrderItem(
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=product.unit_price,
                    quantity=item.quantity,
                    line_total=line_total,
                )
            )

        order = Order(
            order_no=_generate_order_no(payload.order_date),
            customer_id=payload.customer_id,
            order_date=payload.order_date,
            status=OrderStatus.CONFIRMED,
            subtotal=subtotal,
            note=payload.note,
            items=order_items,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    @app.get("/orders/{order_id}", response_model=OrderRead)
    def get_order(order_id: int, db: Session = Depends(_get_db)):
        stmt: Select[tuple[Order]] = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id)
        )
        order = db.scalar(stmt)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    @app.get("/orders", response_model=list[OrderRead])
    def list_orders(
        customer_id: int | None = Query(default=None),
        month: str | None = Query(default=None, description="YYYY-MM"),
        db: Session = Depends(_get_db),
    ):
        filters = []
        if customer_id is not None:
            filters.append(Order.customer_id == customer_id)
        if month:
            first_day, next_month = _month_bounds(month)
            filters.extend([Order.order_date >= first_day, Order.order_date < next_month])

        stmt = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
        if filters:
            stmt = stmt.where(and_(*filters))

        return db.scalars(stmt).all()

    @app.patch("/orders/{order_id}/status", response_model=OrderRead)
    def update_order_status(order_id: int, payload: OrderStatusUpdate, db: Session = Depends(_get_db)):
        stmt = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        order = db.scalar(stmt)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        order.status = payload.status
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    @app.get("/settlements/monthly", response_model=MonthlySettlementRead)
    def monthly_settlement(
        customer_id: int = Query(...),
        month: str = Query(..., description="YYYY-MM"),
        db: Session = Depends(_get_db),
    ):
        customer = db.get(Customer, customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        first_day, next_month = _month_bounds(month)
        due_date = _month_due_date(month, customer.billing_cycle_day)

        stmt = (
            select(Order)
            .where(
                and_(
                    Order.customer_id == customer_id,
                    Order.order_date >= first_day,
                    Order.order_date < next_month,
                    Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.INVOICED]),
                )
            )
            .order_by(Order.order_date.asc(), Order.id.asc())
        )
        orders = db.scalars(stmt).all()

        items = [
            MonthlySettlementItem(
                order_no=order.order_no,
                order_date=order.order_date,
                status=order.status,
                subtotal=order.subtotal,
            )
            for order in orders
        ]
        total_due = sum((order.subtotal for order in orders), Decimal("0.00"))
        return MonthlySettlementRead(
            customer_id=customer.id,
            customer_code=customer.code,
            customer_name=customer.name,
            month=month,
            due_date=due_date,
            total_due=total_due,
            order_count=len(items),
            orders=items,
        )

    return app


app = create_app()
