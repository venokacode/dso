import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProductStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="产品名称")
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="产品编码/SKU")
    description: Mapped[str | None] = mapped_column(Text, comment="产品描述")
    unit: Mapped[str] = mapped_column(String(20), default="件", comment="单位")
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False, comment="单价(分)")
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus), default=ProductStatus.ACTIVE, comment="状态"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Product {self.code} - {self.name}>"
