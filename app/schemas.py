from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut


class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    contact_email: Optional[str] = None
    credit_terms_days: int = Field(default=30, ge=1, le=120)


class CustomerOut(BaseModel):
    id: int
    name: str
    contact_email: Optional[str]
    credit_terms_days: int
    billing_cycle: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    sku: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    unit: str = Field(default="pcs", min_length=1, max_length=20)
    unit_price: float = Field(gt=0)


class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    unit: str
    unit_price: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: int
    expected_ship_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=500)
    items: List[OrderItemCreate] = Field(min_length=1)


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    line_total: float

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: int
    order_no: str
    customer_id: int
    status: str
    order_date: date
    expected_ship_date: Optional[date]
    total_amount: float
    notes: Optional[str]
    invoice_id: Optional[int]
    created_at: datetime
    items: List[OrderItemOut]

    model_config = ConfigDict(from_attributes=True)


class InvoiceOut(BaseModel):
    id: int
    invoice_no: str
    customer_id: int
    billing_month: str
    issued_date: date
    due_date: date
    total_amount: float
    status: str
    settled_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarkInvoiceSettledIn(BaseModel):
    settled: bool = True


class ReceivableSummaryOut(BaseModel):
    customer_id: int
    customer_name: str
    total_unsettled_amount: float
    unsettled_invoices: int

