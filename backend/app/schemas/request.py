from pydantic import BaseModel, EmailStr, Field, field_validator


class PurchaseRequestIn(BaseModel):
    employee_name: str = Field(..., min_length=1, max_length=200)
    employee_email: EmailStr
    department: str = Field(..., min_length=1, max_length=100)
    request_text: str = Field(..., min_length=3, max_length=4000)

    @field_validator("employee_name", "department", "request_text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class PurchaseRequestOut(BaseModel):
    request_id: str
    status: str
    approval_required: bool
    message: str


class RequestDetail(BaseModel):
    request_id: str
    employee_name: str
    employee_email: str
    department: str
    request_text: str
    item: str
    category: str
    quantity: int
    estimated_amount: float
    currency: str
    priority: str
    risk_level: str
    confidence: float
    ai_reasoning: str
    approval_required: bool
    status: str
    approver: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
