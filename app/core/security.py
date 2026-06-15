"""
Authentication helpers shared between the API and the dashboard.
"""

import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

_bearer = HTTPBearer(auto_error=False)


def verify_api_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    """FastAPI dependency — raise 401 if the bearer token is missing or wrong."""
    if credentials is None or not secrets.compare_digest(
        credentials.credentials, settings.API_TOKEN
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def is_authenticated(request: Request) -> bool:
    """Return True if the request carries a valid dashboard session."""
    return bool(request.session.get("auth"))


def require_auth(request: Request):
    """Return a redirect to /login if the session is not authenticated, else None."""
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=303)
    return None


def verify_credentials(username: str, password: str) -> bool:
    """Constant-time comparison of submitted credentials against configured values."""
    return (
        secrets.compare_digest(username.strip(), settings.DASHBOARD_USERNAME)
        and secrets.compare_digest(password, settings.DASHBOARD_PASSWORD)
    )
