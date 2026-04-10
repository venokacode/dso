from datetime import datetime

from pydantic import BaseModel, Field

from app.models.product import ProductStatus


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=200, description="产品名称")
    code: str = Field(..., max_length=50, description="产品编码/SKU")
    description: str | None = Field(None, description="产品描述")
    unit: str = Field("件", max_length=20, description="单位")
    unit_price: int = Field(..., gt=0, description="单价(分)")


class ProductUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    unit: str | None = Field(None, max_length=20)
    unit_price: int | None = Field(None, gt=0)
    status: ProductStatus | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    code: str
    description: str | None
    unit: str
    unit_price: int
    status: ProductStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    total: int
    items: list[ProductResponse]
