"""
ORM model registry.

Importing this package registers every model class with Base.metadata,
which is what init_db() relies on before calling create_all().
"""

from sqlalchemy import Index

from app.models.call import Call
from app.models.call_metrics import CallMetrics
from app.models.caller_preferences import CallerPreferences
from app.models.cdr import AsteriskCDR
from app.models.system_log import SystemLog

# Composite indexes defined here so all referenced columns are already loaded.
Index("idx_calls_call_id", Call.call_id)
Index("idx_calls_timestamp", Call.timestamp)
Index("idx_call_metrics_call_id", CallMetrics.call_id)
Index("idx_asterisk_cdr_src_dst", AsteriskCDR.src, AsteriskCDR.dst)
Index("idx_system_log_timestamp_level", SystemLog.timestamp, SystemLog.level)

__all__ = [
    "AsteriskCDR",
    "Call",
    "CallMetrics",
    "CallerPreferences",
    "SystemLog",
]
