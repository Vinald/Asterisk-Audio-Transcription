import csv
import io

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dashboard._shared import _v
from app.core.database import get_db
from app.core.security import require_auth
from app.services.history import get_all_calls, get_all_cdrs, get_all_metrics_with_caller

router = APIRouter(
    prefix="/export",
    tags=["Exports"],
    responses={
        200: {"description": "CSV file download"},
        303: {"description": "Redirect to login when unauthenticated"},
        500: {"description": "Internal server error"},
    },
)


@router.get(
    "/calls.csv",
    status_code=status.HTTP_200_OK,
    summary="Export calls as CSV",
    description="Download all call records as a CSV file.",
    include_in_schema=False,
)
async def export_calls(request: Request, db: Session = Depends(get_db)):
    """
    Export all call history records to a CSV file:

    Columns: call_id, timestamp, caller_id, extension, language, speaker_id, status,
    q1_input_text, q1_output_text, q1_detected_language, q1_input_audio,
    q2_input_text, q2_output_text, q2_detected_language, q2_input_audio.
    """
    if r := require_auth(request):
        return r
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "call_id", "timestamp", "caller_id", "extension", "language", "speaker_id", "status",
        "q1_input_text", "q1_output_text", "q1_detected_language", "q1_input_audio",
        "q2_input_text", "q2_output_text", "q2_detected_language", "q2_input_audio",
    ])
    for c in get_all_calls(db):
        w.writerow([
            _v(c.call_id), _v(c.timestamp), _v(c.caller_id), _v(c.extension),
            _v(c.language), _v(c.speaker_id), _v(c.status),
            _v(c.q1_input_text), _v(c.q1_output_text), _v(c.q1_detected_language), _v(c.q1_input_audio),
            _v(c.q2_input_text), _v(c.q2_output_text), _v(c.q2_detected_language), _v(c.q2_input_audio),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=calls.csv"},
    )


@router.get(
    "/cdr.csv",
    status_code=status.HTTP_200_OK,
    summary="Export CDR records as CSV",
    description="Download all Asterisk call detail records as a CSV file.",
    include_in_schema=False,
)
async def export_cdr(request: Request, db: Session = Depends(get_db)):
    """
    Export all Asterisk CDR records to a CSV file:

    Columns: uniqueid, call_id, src, dst, calldate, duration, billsec, disposition.
    """
    if r := require_auth(request):
        return r
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["uniqueid", "call_id", "src", "dst", "calldate", "duration", "billsec", "disposition"])
    for row in get_all_cdrs(db):
        w.writerow([
            _v(row.uniqueid), _v(row.call_id), _v(row.src), _v(row.dst),
            _v(row.calldate), _v(row.duration), _v(row.billsec), _v(row.disposition),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cdr.csv"},
    )


@router.get(
    "/metrics.csv",
    status_code=status.HTTP_200_OK,
    summary="Export pipeline metrics as CSV",
    description="Download all pipeline timing metrics as a CSV file.",
    include_in_schema=False,
)
async def export_metrics(request: Request, db: Session = Depends(get_db)):
    """
    Export all pipeline metrics to a CSV file:

    Columns: id, call_id, caller_id, question_number,
    stt_duration, agent_duration, tts_duration, total_duration, audio_url.
    """
    if r := require_auth(request):
        return r
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "id", "call_id", "caller_id", "question_number",
        "stt_duration", "agent_duration", "tts_duration", "total_duration", "audio_url",
    ])
    for row in get_all_metrics_with_caller(db):
        m, caller_id = row[0], row[1]
        w.writerow([
            _v(m.id), _v(m.call_id), _v(caller_id), _v(m.question_number),
            _v(m.stt_duration), _v(m.agent_duration), _v(m.tts_duration),
            _v(m.total_duration), _v(m.audio_url),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=metrics.csv"},
    )
