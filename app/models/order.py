import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="订单号")
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, comment="客户ID"
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.DRAFT, comment="订单状态"
    )
    total_amount: Mapped[int] = mapped_column(Integer, default=0, comment="订单总金额(分)")
    shipping_address: Mapped[str | None] = mapped_column(Text, comment="收货地址")
    notes: Mapped[str | None] = mapped_column(Text, comment="订单备注")
    order_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="下单日期")
    statement_month: Mapped[str | None] = mapped_column(
        String(7), comment="对账月份(YYYY-MM), 用于月结"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped["Customer"] = relationship(back_populates="orders")  # noqa: F821
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order {self.order_no}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False, comment="产品ID"
    )
    product_name: Mapped[str] = mapped_column(String(200), comment="产品名称(快照)")
    product_code: Mapped[str] = mapped_column(String(50), comment="产品编码(快照)")
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False, comment="单价(分, 快照)")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, comment="数量")
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False, comment="小计(分)")
    unit: Mapped[str] = mapped_column(String(20), default="件", comment="单位")

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<OrderItem {self.product_name} x{self.quantity}>"
