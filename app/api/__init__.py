"""API router aggregator package."""

from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.analysis import router as analysis_router
from app.api.history import router as history_router
from app.api.health import router as health_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(analysis_router)
api_router.include_router(history_router)
api_router.include_router(health_router)

__all__ = [
    "api_router",
    "auth_router",
    "analysis_router",
    "history_router",
    "health_router",
]
