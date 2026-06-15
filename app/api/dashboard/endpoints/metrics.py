from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dashboard._shared import _caller_colors, templates
from app.core.database import get_db
from app.core.security import require_auth
from app.services.history import get_metrics_page

router = APIRouter(
    prefix="/dashboard/metrics",
    tags=["Dashboard"],
    responses={
        303: {"description": "Redirect to login when unauthenticated"},
        500: {"description": "Internal server error"},
    },
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Pipeline metrics page",
    description="Render the paginated pipeline metrics table showing per-question timing data.",
    include_in_schema=False,
)
async def metrics_list(
    request: Request,
    page: int = Query(1, description="Page number."),
    db: Session = Depends(get_db),
):
    """
    Display a paginated table of pipeline timing metrics:

    - **page**: Current page number
    - Shows STT, agent, TTS, and total durations per question per call
    """
    if r := require_auth(request):
        return r
    data = get_metrics_page(db, max(1, page))
    return templates.TemplateResponse(request, "metrics.html", {
        "active": "metrics",
        "metrics_rows": data["metrics_rows"],
        "page": max(1, page),
        "total_pages": data["total_pages"],
        "total_count": data["total_count"],
        "caller_colors": _caller_colors([r["caller_id"] for r in data["metrics_rows"]]),
    })
