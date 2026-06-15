from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.params import Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import CallCreate, CallResponse
from app.services import create_call, get_call, get_history, get_stats

router = APIRouter(
    prefix="/history",
    tags=["History"],
    responses={
        404: {"description": "Call record not found"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "",
    response_model=CallResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a call record",
    description="Insert a new call record into the database.",
    response_description="The created call record",
)
async def create_call_record(
    request: CallCreate = Body(
        ...,
        examples=[
            {
                "call_id": "HASH-20260615-143022-42",
                "caller_id": "256700123456",
                "extension": "8446",
                "language": "Luganda",
                "speaker_id": 248,
                "status": "in_progress",
            }
        ],
    ),
    db: Session = Depends(get_db),
):
    """
    Create a new call record with the following information:

    - **call_id**: Asterisk call identifier in the format `HASH-YYYYMMDD-HHMMSS-{seq}`, e.g. `HASH-20260615-143022-42`
    - **caller_id**: Caller phone number as set by Asterisk CALLERID(num), e.g. `256700123456`
    - **extension**: Dialled extension
    - **language**: Full language name as set by the Asterisk dialplan — `English` or `Luganda`
    - **speaker_id**: TTS speaker ID
    - **status**: Current call status (e.g. in_progress, completed, failed)
    """
    return create_call(db, request)


@router.get(
    "",
    response_model=list[CallResponse],
    status_code=status.HTTP_200_OK,
    summary="List call history records",
    description="Return a paginated list of call records ordered by most recent first.",
)
async def list_history(
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return (capped at 1 000)."),
    offset: int = Query(0, ge=0, description="Records to skip for pagination."),
    db: Session = Depends(get_db),
):
    """
    Retrieve a paginated list of all call records.

    - **limit**: Maximum number of records to return (1–1 000)
    - **offset**: Number of records to skip
    """
    return get_history(db, limit=min(limit, 1000), offset=offset)


@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Aggregate call statistics",
    description="Return aggregate statistics across all call records.",
)
async def call_stats(db: Session = Depends(get_db)):
    """
    Retrieve aggregate statistics including:

    - **total_calls**: Total number of call records
    - **languages**: Breakdown of calls by detected language
    - **statuses**: Breakdown of calls by status
    - **avg_durations**: Average STT and total pipeline durations per question number
    """
    return get_stats(db)


@router.get(
    "/{call_id}",
    response_model=CallResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single call record",
    description="Fetch the full record for a single call by its call_id.",
)
async def get_call_detail(call_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a single call record by its Asterisk call_id.

    - **call_id**: The Asterisk unique call identifier
    """
    call = get_call(db, call_id)
    if not call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Call {call_id} not found")
    return call
