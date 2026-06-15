"""Dashboard router — aggregates all session-authenticated HTML endpoint modules."""

from fastapi import APIRouter

from app.api.dashboard.endpoints import auth, calls, exports, logs, metrics, overview

router = APIRouter()

router.include_router(auth.router)
router.include_router(overview.router)
router.include_router(calls.router)
router.include_router(logs.router)
router.include_router(metrics.router)
router.include_router(exports.router)
