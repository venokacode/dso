from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .models import CustomerStatus, OrderStatus


class CustomerCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=1, max_length=255)
    billing_cycle_day: int = Field(default=31, ge=1, le=31)


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    billing_cycle_day: int
    status: CustomerStatus
    created_at: datetime


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    unit_price: Decimal = Field(gt=0)


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    unit_price: Decimal
    active: bool
    created_at: datetime


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: int
    order_date: date
    note: str | None = None
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    customer_id: int
    order_date: date
    status: OrderStatus
    subtotal: Decimal
    note: str | None
    created_at: datetime
    items: list[OrderItemRead]


class MonthlySettlementItem(BaseModel):
    order_no: str
    order_date: date
    status: OrderStatus
    subtotal: Decimal


class MonthlySettlementRead(BaseModel):
    customer_id: int
    customer_code: str
    customer_name: str
    month: str
    due_date: date
    total_due: Decimal
    order_count: int
    orders: list[MonthlySettlementItem]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
