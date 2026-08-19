import os
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import redis.asyncio as redis
from sqlalchemy import text

from app.api.endpoints import router as api_router
from app.api.v1.auth import router as auth_router
from app.config.settings import settings
from app.database import Base, engine
from app.models.user import User  # Registers User model with Base
from app.monitoring import metrics

# Initialize database tables
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


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
)
async def health_check():
    """Liveness probe: verifies the container is alive."""
    return {
        "status": "healthy",
        "service": "AI IT Operations Assistant",
    }


@app.get(
    "/ready",
    summary="Readiness check",
)
async def readiness_check(response: Response):
    """Readiness probe: verifies dependencies (PostgreSQL, Redis, Storage) are reachable."""
    checks = {
        "postgres": "unknown",
        "redis": "unknown",
        "vector_store": "unknown",
    }
    is_ready = True

    # 1. Test PostgreSQL Connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = "connected"
    except Exception as e:
        checks["postgres"] = f"unhealthy: {str(e)}"
        is_ready = False

    # 2. Test Redis Connection
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        r = redis.from_url(redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "connected"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
        is_ready = False

    # 3. Test Vector Store Path
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


# Include Routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


# Prometheus metrics endpoint
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