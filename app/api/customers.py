from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.customer import Customer, CustomerStatus
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)

router = APIRouter(prefix="/customers", tags=["客户管理"])


@router.post("", response_model=CustomerResponse, status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    existing = db.execute(select(Customer).where(Customer.code == payload.code)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"客户编码 {payload.code} 已存在")

    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("", response_model=CustomerListResponse)
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: CustomerStatus | None = None,
    keyword: str | None = Query(None, description="按名称或编码搜索"),
    db: Session = Depends(get_db),
):
    query = select(Customer)
    count_query = select(func.count()).select_from(Customer)

    if status:
        query = query.where(Customer.status == status)
        count_query = count_query.where(Customer.status == status)

    if keyword:
        like_pattern = f"%{keyword}%"
        query = query.where(Customer.name.ilike(like_pattern) | Customer.code.ilike(like_pattern))
        count_query = count_query.where(
            Customer.name.ilike(like_pattern) | Customer.code.ilike(like_pattern)
        )

    total = db.execute(count_query).scalar() or 0
    items = db.execute(
        query.order_by(Customer.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    return CustomerListResponse(total=total, items=items)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    db.delete(customer)
    db.commit()
