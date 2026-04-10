from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from models import CustomerStatus, OrderStatus, StatementStatus


# ── Customer ──────────────────────────────────────────────────────────────────

class CustomerBase(BaseModel):
    code: str
    name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    credit_limit: Optional[Decimal] = Decimal("0")
    payment_terms_days: Optional[int] = 30
    status: Optional[CustomerStatus] = CustomerStatus.active
    notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    payment_terms_days: Optional[int] = None
    status: Optional[CustomerStatus] = None
    notes: Optional[str] = None


class CustomerOut(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


# ── Product ───────────────────────────────────────────────────────────────────

class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    unit: Optional[str] = "件"
    unit_price: Decimal
    is_active: Optional[bool] = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    is_active: Optional[bool] = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


# ── Order Item ────────────────────────────────────────────────────────────────

class OrderItemBase(BaseModel):
    product_id: int
    quantity: Decimal
    unit_price: Decimal
    discount_rate: Optional[Decimal] = Decimal("0")
    notes: Optional[str] = None


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemOut(OrderItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    line_total: Decimal
    product: ProductOut


# ── Order ─────────────────────────────────────────────────────────────────────

class OrderBase(BaseModel):
    customer_id: int
    order_date: date
    delivery_date: Optional[date] = None
    delivery_address: Optional[str] = None
    notes: Optional[str] = None
    discount_amount: Optional[Decimal] = Decimal("0")


class OrderCreate(OrderBase):
    items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    delivery_date: Optional[date] = None
    delivery_address: Optional[str] = None
    notes: Optional[str] = None
    discount_amount: Optional[Decimal] = None
    items: Optional[List[OrderItemCreate]] = None


class OrderOut(OrderBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_no: str
    status: OrderStatus
    subtotal: Decimal
    total_amount: Decimal
    statement_id: Optional[int] = None
    customer: CustomerOut
    items: List[OrderItemOut]
    created_at: datetime
    updated_at: datetime


class OrderListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_no: str
    status: OrderStatus
    order_date: date
    total_amount: Decimal
    customer_id: int
    customer: CustomerOut
    created_at: datetime


# ── Monthly Statement ─────────────────────────────────────────────────────────

class StatementBase(BaseModel):
    customer_id: int
    year: int
    month: int
    notes: Optional[str] = None


class StatementCreate(StatementBase):
    pass


class StatementUpdate(BaseModel):
    status: Optional[StatementStatus] = None
    issued_date: Optional[date] = None
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    notes: Optional[str] = None


class StatementOut(StatementBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    statement_no: str
    total_amount: Decimal
    status: StatementStatus
    issued_date: Optional[date] = None
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    customer: CustomerOut
    orders: List[OrderListOut]
    created_at: datetime
    updated_at: datetime


class StatementListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    statement_no: str
    customer_id: int
    customer: CustomerOut
    year: int
    month: int
    total_amount: Decimal
    status: StatementStatus
    issued_date: Optional[date] = None
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    created_at: datetime


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_customers: int
    active_customers: int
    total_orders_this_month: int
    total_amount_this_month: Decimal
    pending_statements: int
    overdue_statements: int
    overdue_amount: Decimal
