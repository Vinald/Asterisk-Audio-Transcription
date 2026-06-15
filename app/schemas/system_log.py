from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SystemLogBase(BaseModel):
    level: str
    component: str
    event_type: str
    message: str
    call_id: Optional[str] = None
    details: Optional[str] = None


class SystemLogCreate(SystemLogBase):
    """Fields accepted when writing a system event."""
    pass


class SystemLogResponse(SystemLogBase):
    """Full log entry returned by API endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: Optional[datetime] = None
