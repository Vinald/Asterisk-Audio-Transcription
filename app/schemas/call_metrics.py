from typing import Optional

from pydantic import BaseModel, ConfigDict


class CallMetricsBase(BaseModel):
    call_id: str
    question_number: int
    audio_url: Optional[str] = None
    stt_duration: Optional[float] = None
    agent_duration: Optional[float] = None
    tts_duration: Optional[float] = None
    total_duration: Optional[float] = None


class CallMetricsCreate(CallMetricsBase):
    """Fields accepted when recording metrics for a pipeline run."""
    pass


class CallMetricsResponse(CallMetricsBase):
    """Full metrics record returned by API endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
