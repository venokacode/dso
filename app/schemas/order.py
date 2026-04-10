from datetime import datetime

from pydantic import BaseModel, Field

from app.models.order import OrderStatus
from app.schemas.customer import CustomerResponse


class OrderItemCreate(BaseModel):
    product_id: int = Field(..., description="产品ID")
    quantity: int = Field(..., gt=0, description="数量")


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_code: str
    unit_price: int
    quantity: int
    subtotal: int
    unit: str

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    customer_id: int = Field(..., description="客户ID")
    items: list[OrderItemCreate] = Field(..., min_length=1, description="订单项")
    shipping_address: str | None = Field(None, description="收货地址")
    notes: str | None = Field(None, description="订单备注")


class OrderUpdate(BaseModel):
    shipping_address: str | None = None
    notes: str | None = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus = Field(..., description="订单状态")


class OrderResponse(BaseModel):
    id: int
    order_no: str
    customer_id: int
    customer: CustomerResponse | None = None
    status: OrderStatus
    total_amount: int
    shipping_address: str | None
    notes: str | None
    order_date: datetime
    statement_month: str | None
    items: list[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    total: int
    items: list[OrderResponse]
