"""AI Financial Scam Conversation Detector - FastAPI Application Entrypoint."""

from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlencode
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.api import api_router, health_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger
from app.db.session import init_db
from app.schemas.common import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle hook: initializes database and services on startup."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")
    init_db()
    yield
    logger.info("Shutting down application cleanly.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.APP_VERSION,
    description="""
# 🛡️ ScamShield AI - Financial Scam Conversation Detector API

An AI-powered defensive cybersecurity system designed to detect and prevent financial scams
from suspicious chat messages, WhatsApp/SMS conversations, and screenshot uploads **BEFORE** the user executes any payment.

### Key Capabilities:
- **Screenshot OCR Extraction**: Text recognition with regional Tamil & multilingual support.
- **AI & Rule-Based Scam Intelligence**: Multi-provider LLM abstraction with high-precision offline heuristic fallback.
- **Fine-Grained Risk Scoring**: Multi-factor threat breakdown (Urgency, Credential risk, Coercion, Payment vectors).
- **Explainable Fraud Red Flags**: Plain-language explanations of deception mechanics in English and Tamil.
- **Actionable Defense Recommendations**: Step-by-step guidance and immediate national helpline routing (e.g. 1930 / FTC).
- **Full History & Threat Analytics**: Personal threat metrics and history management.

*Defensive Cybersecurity Note: This application is strictly non-transactional and operates only on user-submitted content.*
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------------
cors_origins = settings.BACKEND_CORS_ORIGINS or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if "*" not in cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom application domain exceptions."""
    logger.warning(f"AppException on {request.url.path}: [{exc.error_code}] {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content=ErrorResponse(
            success=False,
            error_code=exc.error_code,
            message=exc.detail,
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic request validation errors."""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    error_details = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        error_details.append({
            "field": loc,
            "message": err.get("msg", "Invalid value"),
            "type": err.get("type", "value_error"),
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            success=False,
            error_code="VALIDATION_ERROR",
            message="Request input validation failed. Please check field types and constraints.",
            details={"errors": error_details},
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle standard Starlette / FastAPI HTTPExceptions."""
    logger.warning(f"HTTPException on {request.url.path}: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content=ErrorResponse(
            success=False,
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for unexpected internal server errors."""
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred while processing your request.",
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Mount Routers
# ---------------------------------------------------------------------------
app.include_router(health_router)  # /health, /ping, /api/v1/health, /api/v1/ping
app.include_router(api_router, prefix=settings.API_V1_STR)

# ---------------------------------------------------------------------------
# Static Files & Frontend App Serving
# ---------------------------------------------------------------------------
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/", tags=["Frontend"])
async def serve_index(request: Request):
    """Serve the Stitch UI frontend if accessed from a browser (Accept: text/html), or JSON discovery metadata otherwise."""
    accept = request.headers.get("accept", "")
    index_path = os.path.join(frontend_dir, "index.html")
    if "text/html" in accept and os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "documentation": "/docs",
        "health_check": "/health",
        "api_v1_prefix": settings.API_V1_STR,
        "disclaimer": "Defensive cybersecurity tool for detecting financial fraud before making payments. No private account scraping or real money transactions performed.",
    }


@app.get("/sw.js", include_in_schema=False)
async def serve_service_worker():
    """Service worker served from the root so it can receive shares for the whole app."""
    return FileResponse(os.path.join(frontend_dir, "sw.js"), media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})


@app.get("/manifest.webmanifest", include_in_schema=False)
async def serve_manifest():
    return FileResponse(os.path.join(frontend_dir, "manifest.webmanifest"), media_type="application/manifest+json")


@app.post("/share-target", include_in_schema=False)
async def share_target_fallback(request: Request):
    """Used only if the service worker isn't active yet: pass shared text to the app via the URL."""
    form = await request.form()
    text = "\n".join(str(form.get(k)) for k in ("title", "text", "url") if form.get(k) and isinstance(form.get(k), str))
    return RedirectResponse(url=f"/?{urlencode({'text': text[:2500]})}" if text.strip() else "/", status_code=303)


@app.get("/app", tags=["Frontend"], include_in_schema=False)
async def serve_app():
    """Direct alias for the frontend UI."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Frontend index.html not found"}
