from fastapi import APIRouter, status

from app.services import get_speakers

router = APIRouter(
    prefix="/speakers",
    tags=["Reference"],
    responses={
        500: {"description": "Internal server error"},
    },
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List available TTS speakers",
    description="Return the map of supported language codes to their default Sunbird TTS speaker IDs.",
    responses={
        200: {
            "description": "Speaker map",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "speakers": {
                            "lug": 248,
                            "eng": 248,
                            "ach": 241,
                            "teo": 242,
                            "nyn": 243,
                            "lgg": 245,
                            "swa": 246,
                        },
                    }
                }
            },
        }
    },
)
async def get_available_speakers():
    """
    Retrieve the full map of language codes to default Sunbird TTS speaker IDs:

    - **lug**: Luganda
    - **eng**: English
    - **ach**: Acholi
    - **teo**: Ateso
    - **nyn**: Runyankore
    - **lgg**: Lugbara
    - **swa**: Swahili
    """
    return {"success": True, "speakers": get_speakers()}
