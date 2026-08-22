import enum
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, Text
from app.database import Base


class RequestStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_PROCESSED = "AUTO_PROCESSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ACTION_FAILED = "ACTION_FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class PurchaseRequest(Base):
    __tablename__ = "requests"

    id = Column(String, primary_key=True)  # e.g. REQ-2026-0001
    request_hash = Column(String, index=True, nullable=False)  # idempotency

    employee_name = Column(String, nullable=False)
    employee_email = Column(String, nullable=False)
    department = Column(String, nullable=False)
    request_text = Column(Text, nullable=False)

    item = Column(String, default="")
    category = Column(String, default="")
    quantity = Column(Integer, default=0)
    estimated_amount = Column(Float, default=0)
    currency = Column(String, default="INR")
    priority = Column(String, default="")
    risk_level = Column(String, default="")
    confidence = Column(Float, default=0)
    ai_reasoning = Column(Text, default="")

    approval_required = Column(Integer, default=0)  # 0/1 (sqlite-friendly bool)
    status = Column(Enum(RequestStatus), default=RequestStatus.RECEIVED)

    notion_page_id = Column(String, default="")
    notion_approval_page_id = Column(String, default="")
    approver = Column(String, default="")

    external_action_id = Column(String, default="")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
