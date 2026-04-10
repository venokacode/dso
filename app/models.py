from datetime import date, datetime, timezone

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True)
    contact_email = Column(String(200), nullable=True)
    credit_terms_days = Column(Integer, nullable=False, default=30)
    billing_cycle = Column(String(20), nullable=False, default="monthly")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    orders = relationship("Order", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(60), nullable=False, unique=True, index=True)
    name = Column(String(160), nullable=False)
    unit = Column(String(20), nullable=False, default="pcs")
    unit_price = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(40), nullable=False, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    order_date = Column(Date, nullable=False, default=date.today)
    expected_ship_date = Column(Date, nullable=True)
    total_amount = Column(Float, nullable=False, default=0.0)
    notes = Column(String(500), nullable=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    invoice = relationship("Invoice", back_populates="orders")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    line_total = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("customer_id", "billing_month", name="uq_customer_month"),)

    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String(40), nullable=False, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    billing_month = Column(String(7), nullable=False, index=True)  # YYYY-MM
    issued_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)
    status = Column(String(20), nullable=False, default="issued", index=True)
    settled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    customer = relationship("Customer", back_populates="invoices")
    orders = relationship("Order", back_populates="invoice")

