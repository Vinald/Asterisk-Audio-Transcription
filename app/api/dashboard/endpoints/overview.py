from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.dashboard._shared import _caller_colors, templates
from app.core.database import get_db
from app.core.security import require_auth
from app.services.history import get_overview

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    responses={
        303: {"description": "Redirect to login when unauthenticated"},
        500: {"description": "Internal server error"},
    },
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Dashboard overview",
    description="Render the main dashboard page with call totals, language breakdown, and recent calls.",
    include_in_schema=False,
)
async def overview(request: Request, db: Session = Depends(get_db)):
    """
    Display the dashboard overview:

    - **total**: Total number of call records
    - **statuses**: Breakdown of calls by status
    - **languages**: Breakdown of calls by detected language
    - **recent**: The 10 most recent call records
    """
    if r := require_auth(request):
        return r
    data = get_overview(db)
    return templates.TemplateResponse(request, "dashboard.html", {
        "active": "overview",
        **data,
        "caller_colors": _caller_colors([c.caller_id for c in data["recent"]]),
    })
