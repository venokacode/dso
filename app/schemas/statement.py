from datetime import datetime

from pydantic import BaseModel, Field

from app.models.statement import StatementStatus
from app.schemas.customer import CustomerResponse
from app.schemas.order import OrderResponse


class StatementGenerate(BaseModel):
    customer_id: int = Field(..., description="客户ID")
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="对账月份(YYYY-MM)")


class StatementStatusUpdate(BaseModel):
    status: StatementStatus = Field(..., description="对账单状态")


class StatementResponse(BaseModel):
    id: int
    statement_no: str
    customer_id: int
    customer: CustomerResponse | None = None
    month: str
    total_amount: int
    order_count: int
    status: StatementStatus
    due_date: datetime | None
    paid_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StatementDetailResponse(StatementResponse):
    orders: list[OrderResponse] = []


class StatementListResponse(BaseModel):
    total: int
    items: list[StatementResponse]
