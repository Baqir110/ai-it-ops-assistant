"""OpsGuard — Infrastructure Reliability, Incident Response & Self-Healing Platform."""

import logging
import os
import uuid
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app
from sqlalchemy import text

from app.api.v1 import (
    audit,
    auth,
    cost,
    detection,
    incidents,
    remediation,
    services,
    simulator,
    slo,
)
from app.api.endpoints import router as legacy_api_router
from app.config.settings import settings
from app.database import Base, engine
from app.logging_config import setup_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.scheduler.jobs import Scheduler

# Configure structured JSON logging
setup_logging(log_level=settings.LOG_LEVEL)
logger = logging.getLogger("app.main")

# Create tables on startup (in production, use Alembic migrations)
Base.metadata.create_all(bind=engine)

# Global scheduler instance
_scheduler: Scheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(
        "OpsGuard %s starting in %s mode", settings.APP_VERSION, settings.ENVIRONMENT
    )

    # Create default admin user if it doesn't exist
    from app.database.connection import SessionLocal
    from app.database.repositories import get_user_by_username
    from app.auth.security import hash_password
    from app.database.models import UserRole

    db = SessionLocal()
    try:
        admin = get_user_by_username(db, settings.DEFAULT_ADMIN_USERNAME)
        if not admin:
            from app.database.repositories import create_user

            create_user(
                db=db,
                username=settings.DEFAULT_ADMIN_USERNAME,
                email="admin@opsguard.local",
                hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                role=UserRole.ADMIN.value,
            )
            logger.info("Default admin user created")
    finally:
        db.close()

    global _scheduler
    _scheduler = Scheduler()
    await _scheduler.start()

    yield

    # Shutdown
    logger.info("Shutting down OpsGuard")
    if _scheduler:
        await _scheduler.stop()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.APP_VERSION,
    description=(
        "Infrastructure Reliability, Incident Response & Self-Healing Platform. "
        "Detection → Incident → Evidence → Diagnosis → Remediation → Verification → Resolution."
    ),
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    return response


# Request ID middleware
@app.middleware("http")
async def add_request_context_and_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    logger.info(
        f"Incoming request: {request.method} {request.url.path}",
        extra={"request_id": request_id},
    )

    try:
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            f"Completed request: {request.method} {request.url.path} "
            f"- Status {response.status_code}",
            extra={"request_id": request_id},
        )

        return response

    except Exception as exc:
        logger.error(
            f"Unhandled exception during "
            f"{request.method} {request.url.path}: {str(exc)}",
            exc_info=True,
            extra={"request_id": request_id},
        )
        raise


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your request.",
            "request_id": request_id,
        },
    )


@app.get("/health")
async def health_check():
    """Liveness probe."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/ready")
async def readiness_check(response: Response):
    """Readiness probe."""
    checks = {
        "postgres": "unknown",
        "redis": "unknown",
    }

    is_ready = True

    # Database check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = "connected"
    except Exception as exc:
        checks["postgres"] = f"unhealthy: {str(exc)}"
        is_ready = False

    # Redis check
    try:
        redis_client = redis.from_url(settings.REDIS_URL, socket_timeout=1.0)
        await redis_client.ping()
        await redis_client.aclose()
        checks["redis"] = "connected"
    except Exception:
        checks["redis"] = "degraded"

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "checks": checks}

    return {"status": "ready", "checks": checks}


# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Mount static files (frontend)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include API routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(services.router, prefix="/api/v1")
app.include_router(remediation.router, prefix="/api/v1")
app.include_router(slo.router, prefix="/api/v1")
app.include_router(cost.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(detection.router, prefix="/api/v1")
app.include_router(simulator.router, prefix="/api/v1")

# Legacy telemetry endpoint (backward compatibility)
app.include_router(legacy_api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Serve the OpsGuard dashboard."""
    from fastapi.responses import HTMLResponse
    import os

    static_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_path):
        with open(static_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(
        content="<h1>OpsGuard</h1><p>Dashboard not found. Build the frontend first.</p>"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
