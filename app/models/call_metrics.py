from sqlalchemy import Column, Float, Integer, String, UniqueConstraint

from app.core.database import Base


class CallMetrics(Base):
    """Per-question pipeline timing and output audio URL."""

    __tablename__ = "call_metrics"

    __table_args__ = (
        UniqueConstraint("call_id", "question_number", name="uq_call_metrics_call_question"),
    )

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String(255), index=True, nullable=False)
    question_number = Column(Integer, nullable=False)
    audio_url = Column(String(2000))
    stt_duration = Column(Float)
    agent_duration = Column(Float)
    tts_duration = Column(Float)
    total_duration = Column(Float)
