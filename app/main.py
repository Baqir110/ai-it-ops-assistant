from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

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
    status_code=200,
    summary="Health check",
)
def health_check():
    return {
        "status": "healthy",
        "service": "AI IT Operations Assistant",
    }


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