from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CDRBase(BaseModel):
    uniqueid: str
    call_id: Optional[str] = None
    src: Optional[str] = None
    dst: Optional[str] = None
    channel: Optional[str] = None
    context: Optional[str] = None
    exten: Optional[str] = None
    calldate: Optional[datetime] = None
    start_time: Optional[datetime] = None
    answer_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    billsec: Optional[int] = None
    disposition: Optional[str] = None
    cause: Optional[str] = None
    cause_txt: Optional[str] = None
    recording_file: Optional[str] = None


class CDRCreate(CDRBase):
    """Fields accepted when inserting a CDR from Asterisk."""
    pass


class CDRResponse(CDRBase):
    """Full CDR record returned by API endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: Optional[datetime] = None
