"""
Call history, dashboard page queries, and CSV export data services.

API-facing functions return ORM objects — endpoints handle Pydantic serialisation.
Dashboard-facing functions return ORM objects for template rendering.
Export-facing functions return full datasets for CSV serialisation.
"""

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AsteriskCDR, Call, CallMetrics, SystemLog
from app.models.caller_preferences import CallerPreferences

PAGE_SIZE = 25


# ---------------------------------------------------------------------------
# API-facing
# ---------------------------------------------------------------------------

def get_history(db: Session, limit: int = 100, offset: int = 0) -> list:
    return db.query(Call).order_by(Call.timestamp.desc()).offset(offset).limit(limit).all()


def get_call(db: Session, call_id: str):
    return db.query(Call).filter(Call.call_id == call_id).first()


def get_stats(db: Session) -> dict:
    total_calls = db.query(func.count(Call.id)).scalar() or 0
    if total_calls == 0:
        return {"total_calls": 0, "languages": {}, "statuses": {}, "avg_durations": {}}

    languages = {
        (r[0] or "unknown"): r[1]
        for r in db.query(Call.language, func.count(Call.id)).group_by(Call.language).all()
    }
    statuses = {
        (r[0] or "unknown"): r[1]
        for r in db.query(Call.status, func.count(Call.id)).group_by(Call.status).all()
    }
    avg_rows = (
        db.query(
            CallMetrics.question_number,
            func.round(func.avg(CallMetrics.total_duration), 2).label("avg_total"),
            func.round(func.avg(CallMetrics.stt_duration), 2).label("avg_stt"),
        )
        .group_by(CallMetrics.question_number)
        .all()
    )
    avg_durations = {
        row.question_number: {"avg_total": row.avg_total or 0, "avg_stt": row.avg_stt or 0}
        for row in avg_rows
    }
    return {
        "total_calls": total_calls,
        "languages": languages,
        "statuses": statuses,
        "avg_durations": avg_durations,
    }


# ---------------------------------------------------------------------------
# Dashboard-facing
# ---------------------------------------------------------------------------

def get_overview(db: Session) -> dict:
    total = db.query(func.count(Call.id)).scalar() or 0
    statuses = {
        (r[0] or "unknown"): r[1]
        for r in db.query(Call.status, func.count(Call.id)).group_by(Call.status).all()
    }
    languages = {
        (r[0] or "unknown"): r[1]
        for r in db.query(Call.language, func.count(Call.id)).group_by(Call.language).all()
    }
    recent = db.query(Call).order_by(Call.id.desc()).limit(10).all()
    return {"total": total, "statuses": statuses, "languages": languages, "recent": recent}


def get_calls_page(
    db: Session,
    page: int = 1,
    status: str | None = None,
    language: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    page = max(1, page)
    q = db.query(Call).order_by(Call.id.desc())
    if status:
        q = q.filter(Call.status == status)
    if language:
        q = q.filter(Call.language == language)
    try:
        if date_from:
            q = q.filter(Call.timestamp >= datetime.strptime(date_from, "%Y-%m-%d"))
        if date_to:
            q = q.filter(
                Call.timestamp < datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            )
    except ValueError:
        pass  # invalid date format — skip date filter, preserve original values for display

    total_count = q.count()
    calls = q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
    return {
        "calls": calls,
        "total_count": total_count,
        "total_pages": total_pages,
        "date_from": date_from or "",
        "date_to": date_to or "",
    }


def get_call_with_metrics(db: Session, call_id: str) -> tuple:
    call = db.query(Call).filter(Call.call_id == call_id).first()
    if not call:
        return None, None
    metrics_by_q = {
        m.question_number: m
        for m in db.query(CallMetrics)
        .filter(CallMetrics.call_id == call_id)
        .order_by(CallMetrics.question_number)
        .all()
    }
    return call, metrics_by_q


def get_logs_page(db: Session, page: int = 1, level: str | None = None) -> dict:
    page = max(1, page)
    q = db.query(SystemLog).order_by(SystemLog.id.desc())
    if level:
        q = q.filter(SystemLog.level == level.upper())
    total_count = q.count()
    logs = q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
    return {"logs": logs, "total_count": total_count, "total_pages": total_pages}


def get_metrics_page(db: Session, page: int = 1) -> dict:
    page = max(1, page)
    q = (
        db.query(CallMetrics, Call.caller_id.label("caller_id"))
        .outerjoin(Call, Call.call_id == CallMetrics.call_id)
        .order_by(CallMetrics.id.desc())
    )
    total_count = q.count()
    rows = q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
    return {
        "metrics_rows": [{"m": row[0], "caller_id": row[1]} for row in rows],
        "total_count": total_count,
        "total_pages": total_pages,
    }


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def create_call(db: Session, data) -> object:
    row = Call(
        call_id=data.call_id,
        caller_id=data.caller_id,
        extension=data.extension,
        language=data.language,
        speaker_id=data.speaker_id,
        status=data.status,
        q1_input_text=data.q1_input_text,
        q1_output_text=data.q1_output_text,
        q1_detected_language=data.q1_detected_language,
        q1_input_audio=data.q1_input_audio,
        q2_input_text=data.q2_input_text,
        q2_output_text=data.q2_output_text,
        q2_detected_language=data.q2_detected_language,
        q2_input_audio=data.q2_input_audio,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_metrics_for_call(db: Session, call_id: str) -> list:
    return (
        db.query(CallMetrics)
        .filter(CallMetrics.call_id == call_id)
        .order_by(CallMetrics.question_number)
        .all()
    )


def create_metrics(db: Session, data) -> object:
    row = CallMetrics(**data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_preferences(db: Session, limit: int = 100, offset: int = 0) -> list:
    return db.query(CallerPreferences).offset(offset).limit(limit).all()


def get_preference(db: Session, caller_id: str) -> object:
    return db.query(CallerPreferences).filter(CallerPreferences.caller_id == caller_id).first()


def upsert_preference(db: Session, caller_id: str, language: str) -> object:
    row = db.query(CallerPreferences).filter(CallerPreferences.caller_id == caller_id).first()
    if row:
        row.language = language
    else:
        row = CallerPreferences(caller_id=caller_id, language=language)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_cdrs(db: Session, limit: int = 100, offset: int = 0) -> list:
    return db.query(AsteriskCDR).order_by(AsteriskCDR.id.desc()).offset(offset).limit(limit).all()


def get_cdr(db: Session, uniqueid: str) -> object:
    return db.query(AsteriskCDR).filter(AsteriskCDR.uniqueid == uniqueid).first()


def create_cdr(db: Session, data) -> object:
    row = AsteriskCDR(**data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_logs(db: Session, limit: int = 100, offset: int = 0, level: str | None = None) -> list:
    q = db.query(SystemLog).order_by(SystemLog.id.desc())
    if level:
        q = q.filter(SystemLog.level == level.upper())
    return q.offset(offset).limit(limit).all()


def create_log(db: Session, data) -> object:
    row = SystemLog(**data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Export-facing
# ---------------------------------------------------------------------------

def get_all_calls(db: Session) -> list:
    return db.query(Call).order_by(Call.id.desc()).all()


def get_all_cdrs(db: Session) -> list:
    return db.query(AsteriskCDR).order_by(AsteriskCDR.id.desc()).all()


def get_all_metrics_with_caller(db: Session) -> list:
    return (
        db.query(CallMetrics, Call.caller_id.label("caller_id"))
        .outerjoin(Call, Call.call_id == CallMetrics.call_id)
        .order_by(CallMetrics.id.desc())
        .all()
    )
