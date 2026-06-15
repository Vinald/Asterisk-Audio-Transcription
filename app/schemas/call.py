from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CallBase(BaseModel):
    call_id: str
    caller_id: Optional[str] = None
    extension: Optional[str] = None
    language: Optional[str] = None
    speaker_id: Optional[int] = None
    status: str = "in_progress"

    q1_input_text: Optional[str] = None
    q1_output_text: Optional[str] = None
    q1_detected_language: Optional[str] = None
    q1_input_audio: Optional[str] = None

    q2_input_text: Optional[str] = None
    q2_output_text: Optional[str] = None
    q2_detected_language: Optional[str] = None
    q2_input_audio: Optional[str] = None


class CallCreate(CallBase):
    """Fields accepted when creating a new call record."""
    pass


class CallResponse(CallBase):
    """Full call record returned by API endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: Optional[datetime] = None
