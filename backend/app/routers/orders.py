import random
import string
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models.customer import Customer
from ..models.product import Product
from ..models.order import Order, OrderItem
from ..schemas import OrderCreate, OrderUpdate, OrderOut

router = APIRouter(prefix="/api/orders", tags=["orders"])

VALID_TRANSITIONS = {
    "pending": ["confirmed", "cancelled"],
    "confirmed": ["shipped", "cancelled"],
    "shipped": ["completed"],
    "completed": [],
    "cancelled": [],
}


def _generate_order_no() -> str:
    today = date.today().strftime("%Y%m%d")
    rand = "".join(random.choices(string.digits, k=6))
    return f"ORD-{today}-{rand}"


@router.get("", response_model=list[OrderOut])
def list_orders(
    customer_id: int | None = Query(None),
    status: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    keyword: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Order).options(joinedload(Order.items), joinedload(Order.customer))
    if customer_id:
        q = q.filter(Order.customer_id == customer_id)
    if status:
        q = q.filter(Order.status == status)
    if start_date:
        q = q.filter(Order.order_date >= start_date)
    if end_date:
        q = q.filter(Order.order_date <= end_date)
    if keyword:
        q = q.filter(Order.order_no.contains(keyword))

    orders = q.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    result = []
    for o in orders:
        d = OrderOut.model_validate(o)
        d.customer_name = o.customer.name if o.customer else None
        result.append(d)
    return result


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.customer))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    result = OrderOut.model_validate(order)
    result.customer_name = order.customer.name if order.customer else None
    return result


@router.post("", response_model=OrderOut)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=400, detail="客户不存在")
    if not data.items:
        raise HTTPException(status_code=400, detail="订单明细不能为空")

    order = Order(
        order_no=_generate_order_no(),
        customer_id=data.customer_id,
        order_date=data.order_date,
        notes=data.notes,
        status="pending",
    )

    total = 0
    for item_data in data.items:
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"产品 ID {item_data.product_id} 不存在")
        amount = product.unit_price * item_data.quantity
        total += amount
        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                product_code=product.code,
                unit=product.unit,
                unit_price=product.unit_price,
                quantity=item_data.quantity,
                amount=amount,
            )
        )

    order.total_amount = total
    db.add(order)
    db.commit()
    db.refresh(order)

    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.customer))
        .filter(Order.id == order.id)
        .first()
    )
    result = OrderOut.model_validate(order)
    result.customer_name = order.customer.name if order.customer else None
    return result


@router.put("/{order_id}", response_model=OrderOut)
def update_order(order_id: int, data: OrderUpdate, db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.customer))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if data.status and data.status != order.status:
        if data.status not in VALID_TRANSITIONS.get(order.status, []):
            raise HTTPException(
                status_code=400,
                detail=f"无法从 {order.status} 变更为 {data.status}",
            )
        order.status = data.status

    if data.notes is not None:
        order.notes = data.notes

    db.commit()
    db.refresh(order)
    result = OrderOut.model_validate(order)
    result.customer_name = order.customer.name if order.customer else None
    return result


@router.delete("/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status not in ("pending", "cancelled"):
        raise HTTPException(status_code=400, detail="只能删除待确认或已取消的订单")
    db.delete(order)
    db.commit()
    return {"ok": True}
