from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI IT Operations Assistant"
    CPU_THRESHOLD: float = 85.0
    RAM_THRESHOLD: float = 85.0
    DISK_THRESHOLD: float = 90.0

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()