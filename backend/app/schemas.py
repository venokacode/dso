from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


# ── Customer ──────────────────────────────────────────────

class CustomerBase(BaseModel):
    name: str
    code: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    payment_terms: int = 30
    credit_limit: int = 0
    notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    payment_terms: Optional[int] = None
    credit_limit: Optional[int] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class CustomerOut(CustomerBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Product ───────────────────────────────────────────────

class ProductBase(BaseModel):
    name: str
    code: str
    unit: str = "件"
    unit_price: int = Field(..., description="单价（分）")
    description: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProductOut(ProductBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Order ─────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_code: Optional[str] = None
    unit: Optional[str] = None
    unit_price: int
    quantity: int
    amount: int

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    customer_id: int
    order_date: date
    notes: Optional[str] = None
    items: list[OrderItemCreate]


class OrderUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[str] = None


class OrderOut(BaseModel):
    id: int
    order_no: str
    customer_id: int
    customer_name: Optional[str] = None
    order_date: date
    status: str
    total_amount: int
    notes: Optional[str] = None
    items: list[OrderItemOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Monthly Invoice ───────────────────────────────────────

class InvoiceOut(BaseModel):
    id: int
    invoice_no: str
    customer_id: int
    customer_name: Optional[str] = None
    year: int
    month: int
    total_amount: int
    order_count: int
    status: str
    notes: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


# ── Dashboard ─────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_customers: int
    total_products: int
    total_orders: int
    orders_this_month: int
    revenue_this_month: int
    pending_invoices: int
    unpaid_amount: int
