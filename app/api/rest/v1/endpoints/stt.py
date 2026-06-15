from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.services import identify_language, transcribe

router = APIRouter(
    prefix="/stt",
    tags=["STT"],
    responses={
        400: {"description": "Transcription or language detection error"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Speech-to-text transcription",
    description="Transcribe an uploaded audio file to plain text using the Sunbird AI STT service.",
    responses={
        200: {
            "description": "Transcription result",
            "content": {
                "application/json": {
                    "example": {"success": True, "transcribed_text": "Oli otya nno"}
                }
            },
        }
    },
)
async def transcribe_audio(
    audio: UploadFile = File(..., description="WAV audio file to transcribe."),
    language: str = Form(
        None,
        description=(
            "ISO 639-3 language code (e.g. eng, lug, ach). "
            "Omit to let the engine detect it automatically."
        ),
    ),
):
    """
    Transcribe a caller's audio file to text:

    - **audio**: WAV file containing the speech to transcribe
    - **language**: Language code hint — omit for automatic detection
    """
    try:
        text = transcribe(await audio.read(), language)
        return {"success": True, "transcribed_text": text}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/language-detect",
    status_code=status.HTTP_200_OK,
    summary="Detect language of a text string",
    description="Identify the language of the supplied text using the Sunbird AI language-ID service.",
    responses={
        200: {
            "description": "Detected language result",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "detected_language": "Luganda",
                        "text": "Oli otya nno",
                    }
                }
            },
        }
    },
)
async def detect_language_endpoint(
    text: str = Form(..., description="Plain text whose language should be identified."),
):
    """
    Identify the language of a text string:

    - **text**: The transcribed or raw text to analyse
    """
    try:
        language = identify_language(text)
        return {"success": True, "detected_language": language, "text": text}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
