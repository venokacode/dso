import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StatementStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    CONFIRMED = "confirmed"
    PAID = "paid"
    OVERDUE = "overdue"


class MonthlyStatement(Base):
    __tablename__ = "monthly_statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    statement_no: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="对账单号"
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, comment="客户ID"
    )
    month: Mapped[str] = mapped_column(String(7), nullable=False, comment="对账月份(YYYY-MM)")
    total_amount: Mapped[int] = mapped_column(Integer, default=0, comment="总金额(分)")
    order_count: Mapped[int] = mapped_column(Integer, default=0, comment="订单数量")
    status: Mapped[StatementStatus] = mapped_column(
        Enum(StatementStatus), default=StatementStatus.PENDING, comment="对账单状态"
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime, comment="到期日")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, comment="付款日期")
    notes: Mapped[str | None] = mapped_column(Text, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped["Customer"] = relationship(back_populates="statements")  # noqa: F821

    def __repr__(self) -> str:
        return f"<MonthlyStatement {self.statement_no} - {self.month}>"
