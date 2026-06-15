from fastapi import APIRouter, Form, HTTPException, status

from app.services import synthesize

router = APIRouter(
    prefix="/tts",
    tags=["TTS"],
    responses={
        400: {"description": "Synthesis error or bad input"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Text-to-speech synthesis",
    description="Synthesize text into speech via the Sunbird AI TTS service.",
    responses={
        200: {
            "description": "Synthesis result with audio URL",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "audio_url": "https://storage.googleapis.com/sb-asr-audio-content-sb-gcp-project-01/tts_audio/20260615_143022_9aeee076_5e2c77d0.wav",
                        "language": "eng",
                        "speaker_id": 248,
                    }
                }
            },
        }
    },
)
async def synthesize_speech(
    text: str = Form(..., description="Text to synthesize into speech."),
    language: str = Form("eng", description="Language code used to select the default speaker (e.g. eng, lug, ach)."),
    speaker_id: int = Form(None, description="Sunbird TTS speaker ID. Defaults to the language default."),
):
    """
    Convert text to speech using the Sunbird AI TTS service:

    - **text**: The text string to synthesize
    - **language**: Language code that determines the default speaker when no speaker_id is given
    - **speaker_id**: Override the default speaker — see GET /api/v1/speakers for available IDs
    """
    try:
        result = synthesize(text, language, speaker_id)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
