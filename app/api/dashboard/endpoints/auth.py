from fastapi import APIRouter, Form, Request, status
from fastapi.responses import RedirectResponse

from app.api.dashboard._shared import templates
from app.core.security import verify_credentials

router = APIRouter(
    tags=["Auth"],
    responses={
        303: {"description": "Redirect after login or logout"},
        401: {"description": "Invalid credentials"},
    },
)


@router.get(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Show login page",
    description="Render the dashboard login form. Redirects to /dashboard if already authenticated.",
    include_in_schema=False,
)
async def login_page(request: Request):
    """
    Display the login form.

    Redirects to **/dashboard** if the session is already authenticated.
    """
    if request.session.get("auth"):
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post(
    "/login",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Submit login credentials",
    description="Validate username and password. Sets the session cookie and redirects to /dashboard on success.",
    include_in_schema=False,
)
async def login_submit(
    request: Request,
    username: str = Form(default=""),
    password: str = Form(default=""),
):
    """
    Authenticate with username and password:

    - **username**: Dashboard username (configured via DASHBOARD_USERNAME)
    - **password**: Dashboard password (configured via DASHBOARD_PASSWORD)

    Redirects to **/dashboard** on success, or re-renders the login form with an error on failure.
    """
    if verify_credentials(username, password):
        request.session["auth"] = True
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Invalid username or password"},
    )


@router.get(
    "/logout",
    status_code=status.HTTP_303_SEE_OTHER,
    summary="Log out",
    description="Clear the session cookie and redirect to the login page.",
    include_in_schema=False,
)
async def logout(request: Request):
    """
    End the current session and redirect to **/login**.
    """
    request.session.clear()
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
