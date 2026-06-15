"""System event logging service."""

import logging

from sqlalchemy.orm import Session

from app.models.system_log import SystemLog

log = logging.getLogger(__name__)


def log_event(
    db: Session,
    level: str,
    component: str,
    event_type: str,
    message: str,
    call_id: str | None = None,
    details: str | None = None,
) -> None:
    try:
        db.add(SystemLog(
            level=level,
            component=component,
            event_type=event_type,
            message=message,
            call_id=call_id,
            details=details,
        ))
        db.commit()
        log.log(
            getattr(logging, level, logging.INFO),
            "[%s] %s: %s — %s",
            component, event_type, message, call_id or "",
        )
    except Exception as e:
        log.error("Failed to write system_log entry: %s", e)
