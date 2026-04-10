from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from ..database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    contact_person = Column(String(100))
    phone = Column(String(50))
    email = Column(String(200))
    address = Column(Text)
    payment_terms = Column(Integer, default=30, comment="账期天数，默认30天")
    credit_limit = Column(Integer, default=0, comment="信用额度（分）")
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    orders = relationship("Order", back_populates="customer")
    invoices = relationship("MonthlyInvoice", back_populates="customer")
