from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.params import Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import CallMetricsCreate, CallMetricsResponse
from app.services import create_metrics, get_metrics_for_call

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
    responses={
        404: {"description": "Metrics not found"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "",
    response_model=CallMetricsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record pipeline metrics",
    description="Store timing and audio-URL data for one pipeline question run.",
    response_description="The created metrics record",
)
async def record_metrics(
    request: CallMetricsCreate = Body(
        ...,
        examples=[
            {
                "call_id": "HASH-20260615-143022-42",
                "question_number": 1,
                "audio_url": "https://storage.googleapis.com/sb-asr-audio-content-sb-gcp-project-01/tts_audio/20260615_143022_9aeee076_5e2c77d0.wav",
                "stt_duration": 1.23,
                "agent_duration": 0.87,
                "tts_duration": 0.45,
                "total_duration": 2.55,
            }
        ],
    ),
    db: Session = Depends(get_db),
):
    """
    Record pipeline timing metrics for a single question within a call:

    - **call_id**: Asterisk call identifier this metric belongs to
    - **question_number**: Which question in the call (1 or 2)
    - **audio_url**: URL of the generated TTS audio file
    - **stt_duration**: Time taken for speech-to-text (seconds)
    - **agent_duration**: Time taken for AI agent response (seconds)
    - **tts_duration**: Time taken for text-to-speech (seconds)
    - **total_duration**: Total end-to-end pipeline time (seconds)
    """
    return create_metrics(db, request)


@router.get(
    "/{call_id}",
    response_model=list[CallMetricsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get metrics for a call",
    description="Return all per-question metrics for a given call_id, ordered by question number.",
)
async def get_call_metrics(call_id: str, db: Session = Depends(get_db)):
    """
    Retrieve all pipeline metrics associated with a specific call.

    - **call_id**: The Asterisk call identifier to look up
    """
    rows = get_metrics_for_call(db, call_id)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No metrics found for call {call_id}")
    return rows
