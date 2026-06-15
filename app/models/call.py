from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class Call(Base):
    """One row per phone call. Q1 data inserted on first AGI run, Q2 on second."""

    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    call_id = Column(String(255), unique=True, index=True, nullable=False)
    caller_id = Column(String(50), index=True)
    extension = Column(String(20), index=True)
    language = Column(String(50))
    speaker_id = Column(Integer)
    status = Column(String(50), default="in_progress", index=True)

    q1_input_text = Column(Text)
    q1_output_text = Column(Text)
    q1_detected_language = Column(String(50))
    q1_input_audio = Column(String(500))

    q2_input_text = Column(Text)
    q2_output_text = Column(Text)
    q2_detected_language = Column(String(50))
    q2_input_audio = Column(String(500))
