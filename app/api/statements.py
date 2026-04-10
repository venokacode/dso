import uuid
from datetime import datetime

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.statement import MonthlyStatement, StatementStatus
from app.schemas.statement import (
    StatementDetailResponse,
    StatementGenerate,
    StatementListResponse,
    StatementResponse,
    StatementStatusUpdate,
)

router = APIRouter(prefix="/statements", tags=["月结对账"])


def _generate_statement_no(month: str) -> str:
    return f"STM{month.replace('-', '')}{uuid.uuid4().hex[:6].upper()}"


@router.post("", response_model=StatementResponse, status_code=201)
def generate_statement(payload: StatementGenerate, db: Session = Depends(get_db)):
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    existing = db.execute(
        select(MonthlyStatement).where(
            MonthlyStatement.customer_id == payload.customer_id,
            MonthlyStatement.month == payload.month,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"客户 {customer.name} 在 {payload.month} 的对账单已存在",
        )

    orders = db.execute(
        select(Order).where(
            Order.customer_id == payload.customer_id,
            Order.statement_month == payload.month,
            Order.status.in_([
                OrderStatus.CONFIRMED,
                OrderStatus.SHIPPED,
                OrderStatus.DELIVERED,
            ]),
        )
    ).scalars().all()

    total_amount = sum(o.total_amount for o in orders)
    order_count = len(orders)

    year, month_num = map(int, payload.month.split("-"))
    base_date = datetime(year, month_num, 1)
    due_date = base_date + relativedelta(months=1, days=customer.payment_terms_days - 1)

    statement = MonthlyStatement(
        statement_no=_generate_statement_no(payload.month),
        customer_id=payload.customer_id,
        month=payload.month,
        total_amount=total_amount,
        order_count=order_count,
        due_date=due_date,
    )
    db.add(statement)
    db.commit()
    db.refresh(statement)
    return statement


@router.get("", response_model=StatementListResponse)
def list_statements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    month: str | None = Query(None, description="对账月份(YYYY-MM)"),
    status: StatementStatus | None = None,
    db: Session = Depends(get_db),
):
    query = select(MonthlyStatement).options(joinedload(MonthlyStatement.customer))
    count_query = select(func.count()).select_from(MonthlyStatement)

    if customer_id:
        query = query.where(MonthlyStatement.customer_id == customer_id)
        count_query = count_query.where(MonthlyStatement.customer_id == customer_id)

    if month:
        query = query.where(MonthlyStatement.month == month)
        count_query = count_query.where(MonthlyStatement.month == month)

    if status:
        query = query.where(MonthlyStatement.status == status)
        count_query = count_query.where(MonthlyStatement.status == status)

    total = db.execute(count_query).scalar() or 0
    items = db.execute(
        query.order_by(MonthlyStatement.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique().scalars().all()

    return StatementListResponse(total=total, items=items)


@router.get("/{statement_id}", response_model=StatementDetailResponse)
def get_statement(statement_id: int, db: Session = Depends(get_db)):
    statement = db.execute(
        select(MonthlyStatement)
        .options(joinedload(MonthlyStatement.customer))
        .where(MonthlyStatement.id == statement_id)
    ).unique().scalar_one_or_none()

    if not statement:
        raise HTTPException(status_code=404, detail="对账单不存在")

    orders = db.execute(
        select(Order)
        .options(joinedload(Order.items))
        .where(
            Order.customer_id == statement.customer_id,
            Order.statement_month == statement.month,
            Order.status.in_([
                OrderStatus.CONFIRMED,
                OrderStatus.SHIPPED,
                OrderStatus.DELIVERED,
            ]),
        )
    ).unique().scalars().all()

    result = StatementDetailResponse.model_validate(statement)
    result.orders = orders
    return result


@router.patch("/{statement_id}/status", response_model=StatementResponse)
def update_statement_status(
    statement_id: int, payload: StatementStatusUpdate, db: Session = Depends(get_db)
):
    statement = db.get(MonthlyStatement, statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="对账单不存在")

    valid_transitions = {
        StatementStatus.PENDING: {StatementStatus.SENT, StatementStatus.CONFIRMED},
        StatementStatus.SENT: {StatementStatus.CONFIRMED, StatementStatus.OVERDUE},
        StatementStatus.CONFIRMED: {StatementStatus.PAID, StatementStatus.OVERDUE},
        StatementStatus.OVERDUE: {StatementStatus.PAID},
        StatementStatus.PAID: set(),
    }

    if payload.status not in valid_transitions.get(statement.status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"无法从 {statement.status.value} 转换到 {payload.status.value}",
        )

    statement.status = payload.status
    if payload.status == StatementStatus.PAID:
        statement.paid_at = datetime.now()

    db.commit()
    db.refresh(statement)
    return statement
