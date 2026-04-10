import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.schemas.order import (
    OrderCreate,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdate,
    OrderUpdate,
)

router = APIRouter(prefix="/orders", tags=["订单管理"])


def _generate_order_no() -> str:
    now = datetime.now()
    return f"ORD{now.strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


def _compute_statement_month(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


@router.post("", response_model=OrderResponse, status_code=201)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    if customer.status != "active":
        raise HTTPException(status_code=400, detail="客户已停用，无法创建订单")

    order = Order(
        order_no=_generate_order_no(),
        customer_id=payload.customer_id,
        shipping_address=payload.shipping_address or customer.address,
        notes=payload.notes,
        statement_month=_compute_statement_month(datetime.now()),
    )

    total = 0
    for item_data in payload.items:
        product = db.get(Product, item_data.product_id)
        if not product:
            raise HTTPException(
                status_code=404, detail=f"产品ID {item_data.product_id} 不存在"
            )
        if product.status != "active":
            raise HTTPException(
                status_code=400, detail=f"产品 {product.name} 已停用"
            )

        subtotal = product.unit_price * item_data.quantity
        order_item = OrderItem(
            product_id=product.id,
            product_name=product.name,
            product_code=product.code,
            unit_price=product.unit_price,
            quantity=item_data.quantity,
            subtotal=subtotal,
            unit=product.unit,
        )
        order.items.append(order_item)
        total += subtotal

    order.total_amount = total

    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=OrderListResponse)
def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    status: OrderStatus | None = None,
    statement_month: str | None = Query(None, description="对账月份(YYYY-MM)"),
    order_no: str | None = Query(None, description="订单号搜索"),
    db: Session = Depends(get_db),
):
    query = select(Order).options(joinedload(Order.items), joinedload(Order.customer))
    count_query = select(func.count()).select_from(Order)

    if customer_id:
        query = query.where(Order.customer_id == customer_id)
        count_query = count_query.where(Order.customer_id == customer_id)

    if status:
        query = query.where(Order.status == status)
        count_query = count_query.where(Order.status == status)

    if statement_month:
        query = query.where(Order.statement_month == statement_month)
        count_query = count_query.where(Order.statement_month == statement_month)

    if order_no:
        query = query.where(Order.order_no.ilike(f"%{order_no}%"))
        count_query = count_query.where(Order.order_no.ilike(f"%{order_no}%"))

    total = db.execute(count_query).scalar() or 0
    items = db.execute(
        query.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique().scalars().all()

    return OrderListResponse(total=total, items=items)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.execute(
        select(Order)
        .options(joinedload(Order.items), joinedload(Order.customer))
        .where(Order.id == order_id)
    ).unique().scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, payload: OrderUpdate, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != OrderStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只有草稿状态的订单可以修改")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)

    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(order_id: int, payload: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    valid_transitions = {
        OrderStatus.DRAFT: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
        OrderStatus.CONFIRMED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
        OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
        OrderStatus.DELIVERED: set(),
        OrderStatus.CANCELLED: set(),
    }

    if payload.status not in valid_transitions.get(order.status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"无法从 {order.status.value} 转换到 {payload.status.value}",
        )

    order.status = payload.status
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != OrderStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只有草稿状态的订单可以删除")
    db.delete(order)
    db.commit()
