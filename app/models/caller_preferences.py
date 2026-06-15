from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base


class CallerPreferences(Base):
    """Stores the preferred language for a recurring caller."""

    __tablename__ = "caller_preferences"

    id = Column(Integer, primary_key=True, index=True)
    caller_id = Column(String(50), unique=True, index=True, nullable=False)
    language = Column(String(50), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
