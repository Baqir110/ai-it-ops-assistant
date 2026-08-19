import os
import uuid
import logging
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import redis.asyncio as redis
from sqlalchemy import text

from app.api.endpoints import router as api_router
from app.api.v1.auth import router as auth_router
from app.config.settings import settings
from app.database import Base, engine
from app.models.user import User
from app.logging_config import setup_logging

# Configure structured JSON logging
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("app.main")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Real-time IT infrastructure telemetry evaluation and RAG-augmented incident response API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
            f"Completed request: {request.method} {request.url.path} - Status {response.status_code}",
            extra={"request_id": request_id},
        )
        return response
    except Exception as exc:
        logger.error(
            f"Unhandled exception during {request.method} {request.url.path}: {str(exc)}",
            exc_info=True,
            extra={"request_id": request_id},
        )
        raise exc


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


@app.get("/health", status_code=status.HTTP_200_OK, summary="Health check")
async def health_check():
    return {"status": "healthy", "service": "AI IT Operations Assistant"}


@app.get("/ready", summary="Readiness check")
async def readiness_check(response: Response):
    checks = {"postgres": "unknown", "redis": "unknown", "vector_store": "unknown"}
    is_ready = True

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = "connected"
    except Exception as e:
        checks["postgres"] = f"unhealthy: {str(e)}"
        is_ready = False

    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        r = redis.from_url(redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "connected"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
        is_ready = False

    vector_store_path = os.getenv("VECTOR_STORE_PATH", "./data/vector_store")
    if os.path.exists(vector_store_path):
        checks["vector_store"] = "available"
    else:
        checks["vector_store"] = "missing_path"
        is_ready = False

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "checks": checks}

    return {"status": "ready", "checks": checks}


app.include_router(api_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
