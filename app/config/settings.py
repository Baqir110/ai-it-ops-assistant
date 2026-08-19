from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI IT Operations Assistant"

    DATABASE_URL: str = "postgresql+psycopg://ops:ops@localhost:5432/ops"
    REDIS_URL: str = "redis://localhost:6379/0"
    OPENAI_API_KEY: str = ""

    CPU_THRESHOLD: float = 85.0
    RAM_THRESHOLD: float = 85.0
    DISK_THRESHOLD: float = 90.0

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
