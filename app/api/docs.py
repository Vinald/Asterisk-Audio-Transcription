"""Landing page, protected API documentation endpoints (/docs, /redoc, /openapi.json)."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/", include_in_schema=False)
async def root(request: Request):
    if request.session.get("auth"):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(request, "index.html")


@router.get("/openapi.json", include_in_schema=False)
async def openapi_schema(request: Request):
    return JSONResponse(request.app.openapi())


@router.get("/docs", include_in_schema=False)
async def docs(request: Request):
    return get_swagger_ui_html(openapi_url="/openapi.json", title=request.app.title)


@router.get("/redoc", include_in_schema=False)
async def redoc(request: Request):
    return get_redoc_html(openapi_url="/openapi.json", title=request.app.title)
