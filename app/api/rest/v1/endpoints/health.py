import httpx
from fastapi import APIRouter, status

from app.core.config import settings

router = APIRouter(
    prefix="/health",
    tags=["Meta"],
    responses={
        500: {"description": "Internal server error"},
    },
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Verify the API is running and probe reachability of upstream Sunbird AI endpoints.",
)
async def health_check():
    """
    Check the health of the HASH PBX service and its upstream dependencies:

    - **stt**: Sunbird AI speech-to-text endpoint
    - **tts**: Sunbird AI text-to-speech endpoint
    - **language_id**: Sunbird AI language identification endpoint
    """
    upstream = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in {
            "stt": settings.STT_URL,
            "tts": settings.TTS_URL,
            "language_id": settings.LANGUAGE_ID_URL,
        }.items():
            try:
                resp = await client.head(url)
                upstream[name] = "ok" if resp.is_success or resp.status_code < 500 else "error"
            except Exception as e:
                upstream[name] = f"error: {type(e).__name__}"

    return {"status": "healthy", "service": "HASH PBX Speech Pipeline", "endpoints": upstream}
