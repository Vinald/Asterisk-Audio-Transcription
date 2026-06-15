from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dashboard._shared import _caller_colors, templates
from app.core.database import get_db
from app.core.security import require_auth
from app.services.history import get_call_with_metrics, get_calls_page

router = APIRouter(
    prefix="/dashboard/calls",
    tags=["Dashboard"],
    responses={
        303: {"description": "Redirect to login when unauthenticated"},
        404: {"description": "Call record not found"},
        500: {"description": "Internal server error"},
    },
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Calls list page",
    description="Render the paginated calls list with optional filters for status, language, and date range.",
    include_in_schema=False,
)
async def calls_list(
    request: Request,
    page: int = Query(1, description="Page number."),
    call_status: Optional[str] = Query(None, alias="status", description="Filter by call status."),
    language: Optional[str] = Query(None, description="Filter by language code."),
    date_from: Optional[str] = Query(None, description="Filter calls on or after this date (YYYY-MM-DD)."),
    date_to: Optional[str] = Query(None, description="Filter calls on or before this date (YYYY-MM-DD)."),
    db: Session = Depends(get_db),
):
    """
    Display a paginated, filterable list of call records:

    - **page**: Current page number
    - **status**: Filter by call status (e.g. completed, failed, in_progress)
    - **language**: Filter by detected language code (e.g. eng, lug, ach)
    - **date_from**: Start of date range (YYYY-MM-DD)
    - **date_to**: End of date range (YYYY-MM-DD)
    """
    if r := require_auth(request):
        return r
    data = get_calls_page(db, max(1, page), call_status, language, date_from, date_to)
    return templates.TemplateResponse(request, "calls.html", {
        "active": "calls",
        "calls": data["calls"],
        "page": max(1, page),
        "total_pages": data["total_pages"],
        "total_count": data["total_count"],
        "caller_colors": _caller_colors([c.caller_id for c in data["calls"]]),
        "filters": {
            "status": call_status,
            "language": language,
            "date_from": data["date_from"],
            "date_to": data["date_to"],
        },
    })


@router.get(
    "/{call_id:path}",
    status_code=status.HTTP_200_OK,
    summary="Call detail page",
    description="Render the detail view for a single call, including per-question pipeline metrics.",
    include_in_schema=False,
)
async def call_detail(request: Request, call_id: str, db: Session = Depends(get_db)):
    """
    Display the full detail page for a single call:

    - **call_id**: The Asterisk call identifier
    - Shows transcript, detected language, agent responses, and timing metrics per question
    """
    if r := require_auth(request):
        return r
    call, metrics_by_q = get_call_with_metrics(db, call_id)
    if not call:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": f"Call {call_id!r} not found", "status_code": 404},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return templates.TemplateResponse(request, "call_detail.html", {
        "active": "calls",
        "call": call,
        "metrics_by_q": metrics_by_q,
    })
