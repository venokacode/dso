from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from ..database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    order_date = Column(Date, nullable=False)
    status = Column(
        String(20), default="pending",
        comment="pending=待确认, confirmed=已确认, shipped=已发货, completed=已完成, cancelled=已取消"
    )
    total_amount = Column(Integer, default=0, comment="订单总金额（分）")
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String(200), nullable=False)
    product_code = Column(String(50))
    unit = Column(String(20))
    unit_price = Column(Integer, nullable=False, comment="下单时单价（分）")
    quantity = Column(Integer, nullable=False)
    amount = Column(Integer, nullable=False, comment="小计金额（分）= unit_price * quantity")

    order = relationship("Order", back_populates="items")
