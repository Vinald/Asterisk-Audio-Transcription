"""Top-level API router — mounts the versioned REST API, dashboard UI, and docs."""

from fastapi import APIRouter

from app.api.dashboard import router as dashboard_router
from app.api.docs import router as docs_router
from app.api.rest.v1 import router as rest_router

router = APIRouter()

router.include_router(rest_router)
router.include_router(dashboard_router)
router.include_router(docs_router)
