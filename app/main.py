"""
HASH PBX — application entry point.

Creates the FastAPI instance, registers middleware, and mounts all routers.
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.api import router as api_router
from app.core.config import settings
from app.core.middleware import DocsAuthMiddleware
from app.heartbeat import start_heartbeat_daemon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    if not os.environ.get("HASH_PBX_NO_HEARTBEAT"):
        start_heartbeat_daemon(interval=60)
    yield
    log.info("Shutdown complete")


app = FastAPI(
    title="HASH PBX — Speech Pipeline API",
    description=(
        "REST interface for the HASH speech pipeline: transcription (STT), "
        "language detection, AI agent responses, speech synthesis (TTS), and "
        "the full end-to-end audio pipeline with call-history persistence."
    ),
    version="1.0.0",
    contact={
        "name": "HASH PBX",
        "email": "sokiror@idi.co.ug",
        "url": "http://vinald.me",
    },
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(DocsAuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.DASHBOARD_SECRET_KEY,
    session_cookie="hash_session",
    max_age=3600,
)

app.include_router(api_router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, log_level="info")
