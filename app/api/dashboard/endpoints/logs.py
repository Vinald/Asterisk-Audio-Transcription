from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dashboard._shared import _caller_colors, templates
from app.core.database import get_db
from app.core.security import require_auth
from app.services.history import get_logs_page

router = APIRouter(
    prefix="/dashboard/logs",
    tags=["Dashboard"],
    responses={
        303: {"description": "Redirect to login when unauthenticated"},
        500: {"description": "Internal server error"},
    },
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="System logs page",
    description="Render the paginated system log viewer with optional level filter.",
    include_in_schema=False,
)
async def logs_list(
    request: Request,
    page: int = Query(1, description="Page number."),
    level: Optional[str] = Query(None, description="Filter by log level: INFO, WARNING, or ERROR."),
    db: Session = Depends(get_db),
):
    """
    Display a paginated list of system log entries:

    - **page**: Current page number
    - **level**: Filter by severity level — INFO, WARNING, or ERROR
    """
    if r := require_auth(request):
        return r
    data = get_logs_page(db, max(1, page), level)
    return templates.TemplateResponse(request, "logs.html", {
        "active": "logs",
        "logs": data["logs"],
        "page": max(1, page),
        "total_pages": data["total_pages"],
        "total_count": data["total_count"],
        "filter_level": level or "",
        "caller_colors": _caller_colors([log.call_id for log in data["logs"]]),
    })
