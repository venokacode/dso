from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models.customer import Customer
from ..schemas import CustomerCreate, CustomerUpdate, CustomerOut

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
def list_customers(
    keyword: str = Query("", description="搜索关键词"),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Customer)
    if keyword:
        q = q.filter(
            or_(
                Customer.name.contains(keyword),
                Customer.code.contains(keyword),
                Customer.contact_person.contains(keyword),
            )
        )
    if is_active is not None:
        q = q.filter(Customer.is_active == is_active)
    total = q.count()
    items = q.order_by(Customer.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items


@router.get("/all", response_model=list[CustomerOut])
def list_all_active_customers(db: Session = Depends(get_db)):
    """Return all active customers (for dropdown selectors)."""
    return db.query(Customer).filter(Customer.is_active == True).order_by(Customer.name).all()


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    return customer


@router.post("", response_model=CustomerOut)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    if db.query(Customer).filter(Customer.code == data.code).first():
        raise HTTPException(status_code=400, detail="客户编码已存在")
    customer = Customer(**data.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, data: CustomerUpdate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    customer.is_active = False
    db.commit()
    return {"ok": True}
