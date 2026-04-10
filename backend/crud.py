from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

import models
import schemas


# ── Sequence helpers ──────────────────────────────────────────────────────────

def _next_order_no(db: Session) -> str:
    today = date.today()
    prefix = today.strftime("ORD%Y%m%d")
    count = db.query(models.Order).filter(
        models.Order.order_no.like(f"{prefix}%")
    ).count()
    return f"{prefix}{count + 1:04d}"


def _next_statement_no(db: Session, year: int, month: int) -> str:
    prefix = f"STM{year}{month:02d}"
    count = db.query(models.MonthlyStatement).filter(
        models.MonthlyStatement.statement_no.like(f"{prefix}%")
    ).count()
    return f"{prefix}{count + 1:04d}"


# ── Customer ──────────────────────────────────────────────────────────────────

def get_customers(db: Session, skip: int = 0, limit: int = 200,
                  status: Optional[str] = None, search: Optional[str] = None):
    q = db.query(models.Customer)
    if status:
        q = q.filter(models.Customer.status == status)
    if search:
        like = f"%{search}%"
        q = q.filter(
            models.Customer.name.ilike(like) |
            models.Customer.code.ilike(like)
        )
    return q.order_by(models.Customer.code).offset(skip).limit(limit).all()


def get_customer(db: Session, customer_id: int):
    return db.query(models.Customer).filter(models.Customer.id == customer_id).first()


def create_customer(db: Session, data: schemas.CustomerCreate):
    obj = models.Customer(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_customer(db: Session, customer_id: int, data: schemas.CustomerUpdate):
    obj = get_customer(db, customer_id)
    if not obj:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


# ── Product ───────────────────────────────────────────────────────────────────

def get_products(db: Session, skip: int = 0, limit: int = 500,
                 is_active: Optional[bool] = None, search: Optional[str] = None):
    q = db.query(models.Product)
    if is_active is not None:
        q = q.filter(models.Product.is_active == is_active)
    if search:
        like = f"%{search}%"
        q = q.filter(
            models.Product.name.ilike(like) |
            models.Product.sku.ilike(like)
        )
    return q.order_by(models.Product.sku).offset(skip).limit(limit).all()


def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()


def create_product(db: Session, data: schemas.ProductCreate):
    obj = models.Product(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_product(db: Session, product_id: int, data: schemas.ProductUpdate):
    obj = get_product(db, product_id)
    if not obj:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


# ── Order ─────────────────────────────────────────────────────────────────────

def _compute_items(items_data: list, db: Session):
    result = []
    subtotal = Decimal("0")
    for item_data in items_data:
        qty = Decimal(str(item_data.quantity))
        price = Decimal(str(item_data.unit_price))
        disc = Decimal(str(item_data.discount_rate or 0))
        line_total = qty * price * (1 - disc)
        subtotal += line_total
        result.append((item_data, line_total))
    return result, subtotal


def get_orders(db: Session, skip: int = 0, limit: int = 200,
               customer_id: Optional[int] = None,
               status: Optional[str] = None,
               year: Optional[int] = None,
               month: Optional[int] = None):
    q = db.query(models.Order)
    if customer_id:
        q = q.filter(models.Order.customer_id == customer_id)
    if status:
        q = q.filter(models.Order.status == status)
    if year:
        q = q.filter(func.strftime('%Y', models.Order.order_date) == str(year))
    if month:
        q = q.filter(func.strftime('%m', models.Order.order_date) == f"{month:02d}")
    return q.order_by(models.Order.order_date.desc(), models.Order.id.desc()).offset(skip).limit(limit).all()


def get_order(db: Session, order_id: int):
    return db.query(models.Order).filter(models.Order.id == order_id).first()


def create_order(db: Session, data: schemas.OrderCreate):
    computed_items, subtotal = _compute_items(data.items, db)
    discount = Decimal(str(data.discount_amount or 0))
    total = subtotal - discount

    order = models.Order(
        order_no=_next_order_no(db),
        customer_id=data.customer_id,
        order_date=data.order_date,
        delivery_date=data.delivery_date,
        delivery_address=data.delivery_address,
        notes=data.notes,
        subtotal=subtotal,
        discount_amount=discount,
        total_amount=total,
    )
    db.add(order)
    db.flush()

    for item_data, line_total in computed_items:
        item = models.OrderItem(
            order_id=order.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            discount_rate=item_data.discount_rate or Decimal("0"),
            line_total=line_total,
            notes=item_data.notes,
        )
        db.add(item)

    db.commit()
    db.refresh(order)
    return order


def update_order(db: Session, order_id: int, data: schemas.OrderUpdate):
    order = get_order(db, order_id)
    if not order:
        return None

    simple_fields = ["status", "delivery_date", "delivery_address", "notes", "discount_amount"]
    for f in simple_fields:
        val = getattr(data, f, None)
        if val is not None:
            setattr(order, f, val)

    if data.items is not None:
        for old_item in order.items:
            db.delete(old_item)
        db.flush()

        computed_items, subtotal = _compute_items(data.items, db)
        discount = Decimal(str(order.discount_amount or 0))
        order.subtotal = subtotal
        order.total_amount = subtotal - discount

        for item_data, line_total in computed_items:
            item = models.OrderItem(
                order_id=order.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                discount_rate=item_data.discount_rate or Decimal("0"),
                line_total=line_total,
                notes=item_data.notes,
            )
            db.add(item)

    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order


def delete_order(db: Session, order_id: int):
    order = get_order(db, order_id)
    if not order:
        return False
    db.delete(order)
    db.commit()
    return True


# ── Monthly Statement ─────────────────────────────────────────────────────────

def get_statements(db: Session, skip: int = 0, limit: int = 200,
                   customer_id: Optional[int] = None,
                   status: Optional[str] = None,
                   year: Optional[int] = None,
                   month: Optional[int] = None):
    q = db.query(models.MonthlyStatement)
    if customer_id:
        q = q.filter(models.MonthlyStatement.customer_id == customer_id)
    if status:
        q = q.filter(models.MonthlyStatement.status == status)
    if year:
        q = q.filter(models.MonthlyStatement.year == year)
    if month:
        q = q.filter(models.MonthlyStatement.month == month)
    return q.order_by(
        models.MonthlyStatement.year.desc(),
        models.MonthlyStatement.month.desc()
    ).offset(skip).limit(limit).all()


def get_statement(db: Session, statement_id: int):
    return db.query(models.MonthlyStatement).filter(
        models.MonthlyStatement.id == statement_id
    ).first()


def create_statement(db: Session, data: schemas.StatementCreate):
    existing = db.query(models.MonthlyStatement).filter(
        and_(
            models.MonthlyStatement.customer_id == data.customer_id,
            models.MonthlyStatement.year == data.year,
            models.MonthlyStatement.month == data.month,
        )
    ).first()
    if existing:
        return existing

    # Pull in all delivered/confirmed orders for that month not yet in a statement
    orders = db.query(models.Order).filter(
        and_(
            models.Order.customer_id == data.customer_id,
            models.Order.statement_id == None,
            models.Order.status.in_([
                models.OrderStatus.confirmed,
                models.OrderStatus.shipped,
                models.OrderStatus.delivered,
            ]),
            func.strftime('%Y', models.Order.order_date) == str(data.year),
            func.strftime('%m', models.Order.order_date) == f"{data.month:02d}",
        )
    ).all()

    total = sum(o.total_amount for o in orders)

    stmt = models.MonthlyStatement(
        statement_no=_next_statement_no(db, data.year, data.month),
        customer_id=data.customer_id,
        year=data.year,
        month=data.month,
        total_amount=total,
        notes=data.notes,
    )
    db.add(stmt)
    db.flush()

    for o in orders:
        o.statement_id = stmt.id

    db.commit()
    db.refresh(stmt)
    return stmt


def update_statement(db: Session, statement_id: int, data: schemas.StatementUpdate):
    stmt = get_statement(db, statement_id)
    if not stmt:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(stmt, field, value)
    stmt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(stmt)
    return stmt


# ── Dashboard ─────────────────────────────────────────────────────────────────

def get_dashboard_stats(db: Session) -> schemas.DashboardStats:
    today = date.today()
    year_str = str(today.year)
    month_str = f"{today.month:02d}"

    total_customers = db.query(func.count(models.Customer.id)).scalar()
    active_customers = db.query(func.count(models.Customer.id)).filter(
        models.Customer.status == models.CustomerStatus.active
    ).scalar()

    total_orders_this_month = db.query(func.count(models.Order.id)).filter(
        func.strftime('%Y', models.Order.order_date) == year_str,
        func.strftime('%m', models.Order.order_date) == month_str,
        models.Order.status != models.OrderStatus.cancelled,
    ).scalar()

    total_amount_this_month = db.query(
        func.coalesce(func.sum(models.Order.total_amount), 0)
    ).filter(
        func.strftime('%Y', models.Order.order_date) == year_str,
        func.strftime('%m', models.Order.order_date) == month_str,
        models.Order.status != models.OrderStatus.cancelled,
    ).scalar()

    pending_statements = db.query(func.count(models.MonthlyStatement.id)).filter(
        models.MonthlyStatement.status.in_([
            models.StatementStatus.open,
            models.StatementStatus.issued,
        ])
    ).scalar()

    overdue_statements = db.query(func.count(models.MonthlyStatement.id)).filter(
        models.MonthlyStatement.status == models.StatementStatus.overdue
    ).scalar()

    overdue_amount = db.query(
        func.coalesce(func.sum(models.MonthlyStatement.total_amount), 0)
    ).filter(
        models.MonthlyStatement.status == models.StatementStatus.overdue
    ).scalar()

    return schemas.DashboardStats(
        total_customers=total_customers,
        active_customers=active_customers,
        total_orders_this_month=total_orders_this_month,
        total_amount_this_month=Decimal(str(total_amount_this_month)),
        pending_statements=pending_statements,
        overdue_statements=overdue_statements,
        overdue_amount=Decimal(str(overdue_amount)),
    )
