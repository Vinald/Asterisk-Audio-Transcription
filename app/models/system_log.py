from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class SystemLog(Base):
    """Structured event log written by the pipeline and API layers."""

    __tablename__ = "system_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    level = Column(String(20), index=True)       # INFO / WARNING / ERROR
    component = Column(String(50), index=True)   # e.g. "pipeline", "api"
    event_type = Column(String(100), index=True) # e.g. "pipeline_complete"

    message = Column(Text)
    call_id = Column(String(255), nullable=True, index=True)
    details = Column(Text, nullable=True)
