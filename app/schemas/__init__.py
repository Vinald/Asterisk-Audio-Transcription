"""
Pydantic request / response schemas.

Each schema module mirrors its corresponding model in app/models/:
  call.py              ↔  models/call.py
  call_metrics.py      ↔  models/call_metrics.py
  caller_preferences.py ↔ models/caller_preferences.py
  cdr.py               ↔  models/cdr.py
  system_log.py        ↔  models/system_log.py

Convention:
  <Model>Base     — shared fields, no auto-generated columns
  <Model>Create   — accepted on write (POST / PUT)
  <Model>Response — returned by API endpoints, includes id / timestamps
                    (from_attributes=True so FastAPI can serialise ORM objects)
"""

from app.schemas.call import CallBase, CallCreate, CallResponse
from app.schemas.call_metrics import CallMetricsBase, CallMetricsCreate, CallMetricsResponse
from app.schemas.caller_preferences import (
    CallerPreferencesBase,
    CallerPreferencesResponse,
    CallerPreferencesUpdate,
)
from app.schemas.cdr import CDRBase, CDRCreate, CDRResponse
from app.schemas.system_log import SystemLogBase, SystemLogCreate, SystemLogResponse

__all__ = [
    "CallBase", "CallCreate", "CallResponse",
    "CallMetricsBase", "CallMetricsCreate", "CallMetricsResponse",
    "CallerPreferencesBase", "CallerPreferencesUpdate", "CallerPreferencesResponse",
    "CDRBase", "CDRCreate", "CDRResponse",
    "SystemLogBase", "SystemLogCreate", "SystemLogResponse",
]
