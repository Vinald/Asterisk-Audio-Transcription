from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.params import Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import CallerPreferencesResponse, CallerPreferencesUpdate
from app.services import get_preference, list_preferences, upsert_preference

router = APIRouter(
    prefix="/preferences",
    tags=["Preferences"],
    responses={
        404: {"description": "Caller preference not found"},
        500: {"description": "Internal server error"},
    },
)


@router.get(
    "",
    response_model=list[CallerPreferencesResponse],
    status_code=status.HTTP_200_OK,
    summary="List caller language preferences",
    description="Return all stored caller language preferences.",
)
async def list_caller_preferences(
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return."),
    offset: int = Query(0, ge=0, description="Records to skip for pagination."),
    db: Session = Depends(get_db),
):
    """
    Retrieve a paginated list of all stored caller language preferences.

    - **limit**: Maximum number of records to return (1–1 000)
    - **offset**: Number of records to skip
    """
    return list_preferences(db, limit=limit, offset=offset)


@router.get(
    "/{caller_id}",
    response_model=CallerPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get preferences for a caller",
    description="Return the stored language preference for a specific caller.",
)
async def get_caller_preference(caller_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the language preference for a single caller.

    - **caller_id**: Caller phone number as set by Asterisk CALLERID(num), e.g. `256700123456`
    """
    row = get_preference(db, caller_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No preference found for caller {caller_id}")
    return row


@router.put(
    "/{caller_id}",
    response_model=CallerPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Set caller language preference",
    description="Create or update the language preference for a caller.",
    response_description="The updated caller preference",
)
async def set_caller_preference(
    caller_id: str,
    request: CallerPreferencesUpdate = Body(
        ...,
        examples=[
            {"language": "Luganda"}
        ],
    ),
    db: Session = Depends(get_db),
):
    """
    Create or update the language preference for a caller.

    - **caller_id**: Caller phone number as set by Asterisk CALLERID(num), e.g. `256700123456`
    - **language**: Full language name as set by the Asterisk dialplan — `English` or `Luganda`
    """
    return upsert_preference(db, caller_id, request.language)
