from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.product import Product, ProductStatus
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["产品管理"])


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    existing = db.execute(select(Product).where(Product.code == payload.code)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"产品编码 {payload.code} 已存在")

    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=ProductListResponse)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: ProductStatus | None = None,
    keyword: str | None = Query(None, description="按名称或编码搜索"),
    db: Session = Depends(get_db),
):
    query = select(Product)
    count_query = select(func.count()).select_from(Product)

    if status:
        query = query.where(Product.status == status)
        count_query = count_query.where(Product.status == status)

    if keyword:
        like_pattern = f"%{keyword}%"
        query = query.where(Product.name.ilike(like_pattern) | Product.code.ilike(like_pattern))
        count_query = count_query.where(
            Product.name.ilike(like_pattern) | Product.code.ilike(like_pattern)
        )

    total = db.execute(count_query).scalar() or 0
    items = db.execute(
        query.order_by(Product.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    return ProductListResponse(total=total, items=items)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    db.delete(product)
    db.commit()
