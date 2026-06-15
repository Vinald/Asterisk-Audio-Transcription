from fastapi import APIRouter, Depends, Query, status
from fastapi.params import Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import SystemLogCreate, SystemLogResponse
from app.services import create_log, list_logs

router = APIRouter(
    prefix="/logs",
    tags=["Logs"],
    responses={
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "",
    response_model=SystemLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Write a system log entry",
    description="Record a structured system event (INFO / WARNING / ERROR).",
    response_description="The created log entry",
)
async def write_log(
    request: SystemLogCreate = Body(
        ...,
        examples=[
            {
                "level": "INFO",
                "component": "pipeline",
                "event_type": "pipeline_complete",
                "message": "Pipeline completed successfully for call HASH-20260615-143022-42",
                "call_id": "HASH-20260615-143022-42",
                "details": None,
            }
        ],
    ),
    db: Session = Depends(get_db),
):
    """
    Record a structured system event:

    - **level**: Severity level — INFO, WARNING, or ERROR
    - **component**: Source component (e.g. pipeline, api, stt, tts)
    - **event_type**: Machine-readable event identifier (e.g. pipeline_complete, stt_error)
    - **message**: Human-readable description of the event
    - **call_id**: Associated call identifier (optional)
    - **details**: Additional JSON or text details (optional)
    """
    return create_log(db, request)


@router.get(
    "",
    response_model=list[SystemLogResponse],
    status_code=status.HTTP_200_OK,
    summary="List system log entries",
    description="Return paginated system log entries, newest first. Optionally filter by level.",
)
async def list_log_entries(
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return."),
    offset: int = Query(0, ge=0, description="Records to skip for pagination."),
    level: str | None = Query(None, description="Filter by severity level: INFO, WARNING, or ERROR."),
    db: Session = Depends(get_db),
):
    """
    Retrieve a paginated list of system log entries.

    - **limit**: Maximum number of records to return (1–1 000)
    - **offset**: Number of records to skip
    - **level**: Optional filter — INFO, WARNING, or ERROR
    """
    return list_logs(db, limit=limit, offset=offset, level=level)
