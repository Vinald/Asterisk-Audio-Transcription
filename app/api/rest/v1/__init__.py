"""API v1 router — aggregates all /api/v1/* endpoint modules."""

from fastapi import APIRouter, Depends

from app.api.rest.v1.endpoints import (
    agent, cdr, health, history, logs, metrics, pipeline, preferences, speakers, stt, tts,
)
from app.core.security import verify_api_token

_auth = [Depends(verify_api_token)]

router = APIRouter(prefix="/api/v1")

router.include_router(health.router)  # exempt — docker healthcheck sends no auth header
router.include_router(stt.router, dependencies=_auth)
router.include_router(tts.router, dependencies=_auth)
router.include_router(agent.router, dependencies=_auth)
router.include_router(pipeline.router, dependencies=_auth)
router.include_router(speakers.router, dependencies=_auth)
router.include_router(history.router, dependencies=_auth)
router.include_router(metrics.router, dependencies=_auth)
router.include_router(preferences.router, dependencies=_auth)
router.include_router(cdr.router, dependencies=_auth)
router.include_router(logs.router, dependencies=_auth)
