from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import run_pipeline

router = APIRouter(
    prefix="/pipeline",
    tags=["Pipeline"],
    responses={
        400: {"description": "Pipeline error or bad input"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Full audio pipeline (STT → agent → TTS)",
    description="Run the complete speech-to-text → AI agent → text-to-speech pipeline in one request.",
    responses={
        200: {
            "description": "Pipeline result with transcription, agent reply, and TTS audio URL",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "input_text": "I have a headache",
                        "output_text": "How long have you had the headache?",
                        "detected_language": "English",
                        "output_audio_url": "https://storage.googleapis.com/sb-asr-audio-content-sb-gcp-project-01/tts_audio/20260615_143022_9aeee076_5e2c77d0.wav",
                        "speaker_id": 248,
                        "conversation_id": None,
                    }
                }
            },
        }
    },
)
async def full_pipeline(
    audio: UploadFile = File(..., description="WAV audio file to process."),
    language: str = Form(None, description="Force a language code for STT and TTS. Omit to auto-detect."),
    speaker_id: int = Form(None, description="TTS speaker ID override. Defaults to the language default."),
    auto_detect: bool = Form(True, description="Detect language from transcribed text when no language is forced."),
    call_id: str = Form(None, description="Optional call ID attached to system-event log entries."),
    db: Session = Depends(get_db),
):
    """
    Run the end-to-end speech pipeline:

    - **audio**: WAV file containing the caller's speech
    - **language**: Force a specific language code (e.g. eng, lug, ach) — skips auto-detection
    - **speaker_id**: Sunbird TTS speaker ID to use for synthesis
    - **auto_detect**: When True and no language is forced, detects language from the transcription
    - **call_id**: Asterisk call identifier used to associate log entries with the call record

    Steps executed: transcribe audio → detect language → query AI agent → synthesize reply.
    The temporary audio file is always cleaned up regardless of success or failure.
    """
    try:
        result = run_pipeline(
            db, await audio.read(), audio.filename, language, speaker_id, auto_detect, call_id
        )
        return {
            "success": True,
            "input_text": result["input_text"],
            "output_text": result["output_text"],
            "detected_language": result["detected_language"],
            "output_audio_url": result["output_audio_url"],
            "speaker_id": result["speaker_id"],
            "conversation_id": result.get("conversation_id"),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
