"""Centralized application configuration.

All configuration is driven by environment variables with safe local
development defaults. Never commit real secrets — see .env.example.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """OpsGuard application settings."""

    # --- Project ---
    PROJECT_NAME: str = "OpsGuard"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg://ops:ops@localhost:5432/ops"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Auth ---
    JWT_SECRET_KEY: str = Field(
        default="change-me-in-production",
        description="Secret key for JWT signing. MUST be overridden in production.",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = Field(
        default="admin",
        description="Default admin password. Change immediately in production.",
    )

    # --- AI / LLM ---
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    AI_ENABLED: bool = False

    # --- RAG / Vector Store ---
    VECTOR_STORE_PATH: str = "./data/chroma_db"
    RUNBOOKS_PATH: str = "./data/runbooks"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # --- HTTP Monitor ---
    HTTP_MONITOR_INTERVAL_SECONDS: int = 30
    HTTP_MONITOR_TIMEOUT_SECONDS: float = 5.0
    HTTP_MONITOR_FAILURE_THRESHOLD: int = 3
    HTTP_MONITOR_LATENCY_THRESHOLD_MS: float = 2000.0

    # --- Prometheus ---
    PROMETHEUS_URL: str = "http://localhost:9090"
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_QUERY_TIMEOUT: float = 10.0

    # --- Detection Thresholds ---
    CPU_THRESHOLD: float = 85.0
    RAM_THRESHOLD: float = 85.0
    DISK_THRESHOLD: float = 90.0
    HTTP_ERROR_RATE_THRESHOLD: float = 5.0
    HTTP_LATENCY_P95_THRESHOLD_MS: float = 500.0
    SSL_CERT_EXPIRY_DAYS: int = 14

    # --- Incident Management ---
    INCIDENT_AUTO_RESOLVE_ENABLED: bool = True
    INCIDENT_DEDUP_WINDOW_MINUTES: int = 30
    EVIDENCE_COLLECTION_TIMEOUT: float = 30.0
    VERIFICATION_INTERVAL_SECONDS: int = 15
    VERIFICATION_MAX_ATTEMPTS: int = 5

    # --- Remediation ---
    REMEDIATION_AUTO_APPROVE_LOW_RISK: bool = False
    REMEDIATION_MAX_RETRIES: int = 2

    # --- SLO ---
    SLO_EVALUATION_INTERVAL_SECONDS: int = 300

    # --- Cost ---
    COST_ANALYSIS_INTERVAL_SECONDS: int = 3600

    # --- Security ---
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    AUDIT_LOG_RETENTION_DAYS: int = 365
    RATE_LIMIT_ENABLED: bool = True

    # --- Observability ---
    OTEL_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    LOKI_URL: str = "http://localhost:3100"
    LOKI_ENABLED: bool = False

    # --- Failure Simulator (DEV ONLY) ---
    FAILURE_SIMULATOR_ENABLED: bool = False

    @field_validator("CORS_ALLOWED_ORIGINS")
    @classmethod
    def _split_cors(cls, v: str) -> str:
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
