from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base


class AsteriskCDR(Base):
    """Call detail record written by Asterisk for every completed call."""

    __tablename__ = "asterisk_cdr"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    uniqueid = Column(String(255), unique=True, index=True)
    call_id = Column(String(255), index=True)

    src = Column(String(50), index=True)
    dst = Column(String(50), index=True)
    channel = Column(String(255))
    context = Column(String(100))
    exten = Column(String(50), index=True)

    calldate = Column(DateTime, index=True)
    start_time = Column(DateTime)
    answer_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Integer)
    billsec = Column(Integer)

    disposition = Column(String(50), index=True)
    cause = Column(String(50))
    cause_txt = Column(String(255))
    recording_file = Column(String(255), nullable=True)
