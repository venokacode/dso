from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Date, DateTime,
    ForeignKey, Enum as SAEnum, Boolean
)
from sqlalchemy.orm import relationship
import enum

from database import Base


class CustomerStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class OrderStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class StatementStatus(str, enum.Enum):
    open = "open"
    issued = "issued"
    paid = "paid"
    overdue = "overdue"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    contact_person = Column(String(100))
    email = Column(String(200))
    phone = Column(String(50))
    address = Column(Text)
    credit_limit = Column(Numeric(12, 2), default=0)
    payment_terms_days = Column(Integer, default=30)
    status = Column(SAEnum(CustomerStatus), default=CustomerStatus.active)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders = relationship("Order", back_populates="customer")
    statements = relationship("MonthlyStatement", back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    unit = Column(String(50), default="件")
    unit_price = Column(Numeric(12, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(SAEnum(OrderStatus), default=OrderStatus.draft)
    order_date = Column(Date, nullable=False, default=date.today)
    delivery_date = Column(Date)
    delivery_address = Column(Text)
    notes = Column(Text)
    subtotal = Column(Numeric(12, 2), default=0)
    discount_amount = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2), default=0)
    statement_id = Column(Integer, ForeignKey("monthly_statements.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    statement = relationship("MonthlyStatement", back_populates="orders")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    discount_rate = Column(Numeric(5, 4), default=0)
    line_total = Column(Numeric(12, 2), nullable=False)
    notes = Column(Text)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class MonthlyStatement(Base):
    __tablename__ = "monthly_statements"

    id = Column(Integer, primary_key=True, index=True)
    statement_no = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    total_amount = Column(Numeric(12, 2), default=0)
    status = Column(SAEnum(StatementStatus), default=StatementStatus.open)
    issued_date = Column(Date)
    due_date = Column(Date)
    paid_date = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="statements")
    orders = relationship("Order", back_populates="statement")
