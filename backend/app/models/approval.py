from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from app.database import Base


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String, ForeignKey("requests.id"), nullable=False, index=True)
    status = Column(String, default="PENDING")  # PENDING | APPROVED | REJECTED | OVERRIDDEN
    approver = Column(String, default="")
    decision = Column(String, default="")
    reason = Column(String, default="")
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
