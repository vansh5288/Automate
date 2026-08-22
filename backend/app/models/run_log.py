from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from app.database import Base


class RunLog(Base):
    __tablename__ = "run_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, unique=True, index=True, nullable=False)  # RUN-000123
    request_id = Column(String, ForeignKey("requests.id"), nullable=False, index=True)
    event = Column(String, nullable=False)      # e.g. AI_CLASSIFIED, EXTERNAL_ACTION
    status = Column(String, nullable=False)     # SUCCESS | FAILURE | INFO
    action = Column(String, default="")
    actor = Column(String, default="system")
    reason = Column(Text, default="")
    error = Column(Text, default="")
    external_action_id = Column(String, default="")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
