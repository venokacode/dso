from __future__ import annotations

from calendar import monthrange
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db, init_db
from app.models import Customer, Order, OrderLine, OrderStatus
from app.schemas import (
    CustomerCreate,
    CustomerOut,
    MonthlyStatementLine,
    MonthlyStatementOut,
    OrderCreate,
    OrderLineOut,
    OrderOut,
    OrderStatusUpdate,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="DSO 大客户订单",
    description="月结对账，无在线支付。客户下单后按账期汇总。",
    version="0.1.0",
    lifespan=lifespan,
)


def _order_to_out(o: Order) -> OrderOut:
    lines = [
        OrderLineOut(
            id=ln.id,
            sku=ln.sku,
            description=ln.description,
            quantity=ln.quantity,
            unit_price=ln.unit_price,
            line_total=ln.line_total,
        )
        for ln in o.lines
    ]
    subtotal = sum((ln.line_total for ln in lines), Decimal("0"))
    return OrderOut(
        id=o.id,
        customer_id=o.customer_id,
        external_ref=o.external_ref,
        status=o.status,
        currency=o.currency,
        order_date=o.order_date,
        notes=o.notes,
        created_at=o.created_at,
        updated_at=o.updated_at,
        lines=lines,
        subtotal=subtotal,
    )


@app.post("/customers", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerCreate, db: Session = Depends(get_db)):
    exists = db.scalar(select(Customer).where(Customer.code == body.code))
    if exists:
        raise HTTPException(status_code=409, detail="客户编码已存在")
    c = Customer(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@app.get("/customers", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    return list(db.scalars(select(Customer).order_by(Customer.id)).all())


@app.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    c = db.get(Customer, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail="客户不存在")
    return c


@app.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(body: OrderCreate, db: Session = Depends(get_db)):
    cust = db.get(Customer, body.customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="客户不存在")
    o = Order(
        customer_id=body.customer_id,
        external_ref=body.external_ref,
        currency=body.currency,
        order_date=body.order_date or date.today(),
        notes=body.notes,
        status=OrderStatus.draft,
    )
    for ln in body.lines:
        o.lines.append(
            OrderLine(
                sku=ln.sku,
                description=ln.description,
                quantity=ln.quantity,
                unit_price=ln.unit_price,
            )
        )
    db.add(o)
    db.commit()
    db.refresh(o)
    loaded = db.scalar(
        select(Order).options(selectinload(Order.lines)).where(Order.id == o.id)
    )
    assert loaded is not None
    return _order_to_out(loaded)


@app.get("/orders", response_model=list[OrderOut])
def list_orders(
    customer_id: int | None = None,
    status_filter: OrderStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    q = select(Order).options(selectinload(Order.lines)).order_by(Order.id.desc())
    if customer_id is not None:
        q = q.where(Order.customer_id == customer_id)
    if status_filter is not None:
        q = q.where(Order.status == status_filter)
    rows = db.scalars(q).all()
    return [_order_to_out(o) for o in rows]


@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    o = db.scalar(select(Order).options(selectinload(Order.lines)).where(Order.id == order_id))
    if not o:
        raise HTTPException(status_code=404, detail="订单不存在")
    return _order_to_out(o)


@app.patch("/orders/{order_id}/status", response_model=OrderOut)
def update_order_status(order_id: int, body: OrderStatusUpdate, db: Session = Depends(get_db)):
    o = db.scalar(select(Order).options(selectinload(Order.lines)).where(Order.id == order_id))
    if not o:
        raise HTTPException(status_code=404, detail="订单不存在")
    o.status = body.status
    db.commit()
    db.refresh(o)
    return _order_to_out(o)


@app.get("/statements/monthly", response_model=MonthlyStatementOut)
def monthly_statement(
    customer_id: int,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
):
    cust = db.get(Customer, customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="客户不存在")

    start = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    end = date(year, month, last_day)

    orders = db.scalars(
        select(Order)
        .options(selectinload(Order.lines))
        .where(
            and_(
                Order.customer_id == customer_id,
                Order.order_date >= start,
                Order.order_date <= end,
                Order.status != OrderStatus.cancelled,
            )
        )
        .order_by(Order.order_date, Order.id)
    ).all()

    if not orders:
        return MonthlyStatementOut(
            customer_id=customer_id,
            year=year,
            month=month,
            currency="CNY",
            order_count=0,
            total_amount=Decimal("0"),
            orders=[],
        )

    currency = orders[0].currency
    lines_out: list[MonthlyStatementLine] = []
    total = Decimal("0")
    for o in orders:
        sub = o.subtotal
        total += sub
        lines_out.append(
            MonthlyStatementLine(
                order_id=o.id,
                order_date=o.order_date,
                external_ref=o.external_ref,
                status=o.status,
                subtotal=sub,
            )
        )

    mixed = {o.currency for o in orders}
    if len(mixed) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"该月订单币种不一致: {sorted(mixed)}，请按币种拆分对账",
        )

    return MonthlyStatementOut(
        customer_id=customer_id,
        year=year,
        month=month,
        currency=currency,
        order_count=len(orders),
        total_amount=total,
        orders=lines_out,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
