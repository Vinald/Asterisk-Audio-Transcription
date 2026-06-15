"""Application middleware."""

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import is_authenticated

_PROTECTED_DOCS = {"/openapi.json", "/docs", "/redoc"}


class DocsAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PROTECTED_DOCS and not is_authenticated(request):
            return RedirectResponse("/login", status_code=303)
        return await call_next(request)
