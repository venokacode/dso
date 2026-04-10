from datetime import datetime

from pydantic import BaseModel, Field

from app.models.customer import CustomerStatus


class CustomerCreate(BaseModel):
    name: str = Field(..., max_length=200, description="客户名称")
    code: str = Field(..., max_length=50, description="客户编码")
    contact_person: str | None = Field(None, max_length=100, description="联系人")
    contact_phone: str | None = Field(None, max_length=50, description="联系电话")
    contact_email: str | None = Field(None, max_length=200, description="联系邮箱")
    address: str | None = Field(None, description="地址")
    billing_address: str | None = Field(None, description="账单地址")
    payment_terms_days: int = Field(30, ge=0, description="账期天数")
    credit_limit: int = Field(0, ge=0, description="信用额度(分)")
    notes: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    contact_person: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    address: str | None = None
    billing_address: str | None = None
    payment_terms_days: int | None = Field(None, ge=0)
    credit_limit: int | None = Field(None, ge=0)
    status: CustomerStatus | None = None
    notes: str | None = None


class CustomerResponse(BaseModel):
    id: int
    name: str
    code: str
    contact_person: str | None
    contact_phone: str | None
    contact_email: str | None
    address: str | None
    billing_address: str | None
    payment_terms_days: int
    credit_limit: int
    status: CustomerStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    total: int
    items: list[CustomerResponse]
