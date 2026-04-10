import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CustomerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="客户名称")
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="客户编码")
    contact_person: Mapped[str | None] = mapped_column(String(100), comment="联系人")
    contact_phone: Mapped[str | None] = mapped_column(String(50), comment="联系电话")
    contact_email: Mapped[str | None] = mapped_column(String(200), comment="联系邮箱")
    address: Mapped[str | None] = mapped_column(Text, comment="地址")
    billing_address: Mapped[str | None] = mapped_column(Text, comment="账单地址")
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, comment="账期天数(月结)")
    credit_limit: Mapped[int] = mapped_column(Integer, default=0, comment="信用额度(分)")
    status: Mapped[CustomerStatus] = mapped_column(
        Enum(CustomerStatus), default=CustomerStatus.ACTIVE, comment="状态"
    )
    notes: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    orders: Mapped[list["Order"]] = relationship(back_populates="customer")  # noqa: F821
    statements: Mapped[list["MonthlyStatement"]] = relationship(back_populates="customer")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Customer {self.code} - {self.name}>"
