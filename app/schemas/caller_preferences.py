from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CallerPreferencesBase(BaseModel):
    caller_id: str
    language: str


class CallerPreferencesUpdate(BaseModel):
    """Fields that may be updated for an existing caller."""
    language: str


class CallerPreferencesResponse(CallerPreferencesBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: Optional[datetime] = None
