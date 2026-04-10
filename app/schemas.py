from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models import BillingCycle, OrderStatus


class CustomerCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=256)
    billing_cycle: BillingCycle = BillingCycle.monthly
    contact_email: str | None = None
    notes: str | None = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    billing_cycle: BillingCycle
    contact_email: str | None
    notes: str | None
    created_at: datetime


class OrderLineIn(BaseModel):
    sku: str = Field(..., min_length=1, max_length=64)
    description: str | None = Field(None, max_length=512)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)


class OrderCreate(BaseModel):
    customer_id: int
    external_ref: str | None = Field(None, max_length=128)
    currency: str = Field(default="CNY", max_length=8)
    order_date: date | None = None
    notes: str | None = None
    lines: list[OrderLineIn] = Field(default_factory=list)


class OrderLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    description: str | None
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    external_ref: str | None
    status: OrderStatus
    currency: str
    order_date: date
    notes: str | None
    created_at: datetime
    updated_at: datetime | None
    lines: list[OrderLineOut]
    subtotal: Decimal


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class MonthlyStatementLine(BaseModel):
    order_id: int
    order_date: date
    external_ref: str | None
    status: OrderStatus
    subtotal: Decimal


class MonthlyStatementOut(BaseModel):
    customer_id: int
    year: int
    month: int
    currency: str
    order_count: int
    total_amount: Decimal
    orders: list[MonthlyStatementLine]
