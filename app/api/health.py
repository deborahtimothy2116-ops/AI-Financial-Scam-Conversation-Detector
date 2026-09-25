"""Health and System Status Check API Endpoints."""

import time
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.schemas.common import APIResponse
from app.services.ocr_service import ocr_service

router = APIRouter(tags=["System Health"])
START_TIME = time.time()


@router.get("/health", summary="System Health Status Check")
@router.get("/api/v1/health", summary="System Health Status Check (v1)")
def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check verifying database connectivity, OCR engine, and LLM configuration."""
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    ocr_available = getattr(ocr_service, "is_available", lambda: False)()

    health_data: Dict[str, Any] = {
        "status": "online" if db_status == "healthy" else "degraded",
        "app_name": settings.PROJECT_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "database": db_status,
        "llm_provider": settings.LLM_PROVIDER,
        "ocr_engine_ready": ocr_available,
        "uptime_seconds": round(time.time() - START_TIME, 1),
    }

    return APIResponse(
        message="System operational",
        data=health_data,
    )


@router.get("/ping", summary="Liveness ping")
@router.get("/api/v1/ping", summary="Liveness ping (v1)")
def ping():
    """Lightweight ping endpoint for load balancer liveness probe."""
    return {"status": "ok", "pong": True}
