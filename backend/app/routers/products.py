from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models.product import Product
from ..schemas import ProductCreate, ProductUpdate, ProductOut

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(
    keyword: str = Query("", description="搜索关键词"),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Product)
    if keyword:
        q = q.filter(
            or_(
                Product.name.contains(keyword),
                Product.code.contains(keyword),
            )
        )
    if is_active is not None:
        q = q.filter(Product.is_active == is_active)
    return q.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size).all()


@router.get("/all", response_model=list[ProductOut])
def list_all_active_products(db: Session = Depends(get_db)):
    """Return all active products (for dropdown selectors)."""
    return db.query(Product).filter(Product.is_active == True).order_by(Product.name).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    return product


@router.post("", response_model=ProductOut)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.code == data.code).first():
        raise HTTPException(status_code=400, detail="产品编码已存在")
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    product.is_active = False
    db.commit()
    return {"ok": True}
