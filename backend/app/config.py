from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "PDFKit SaaS"
    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str = "postgresql+asyncpg://pdfkit:pdfkit@localhost:5432/pdfkit"

    REDIS_URL: str = "redis://localhost:6379/0"

    S3_BUCKET: str = "pdfkit"
    S3_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    S3_ENDPOINT_URL: str | None = "http://localhost:9000"
    # Public URL browsers use to reach MinIO (may differ from internal S3_ENDPOINT_URL)
    S3_PUBLIC_URL: str | None = None

    MAX_FILE_SIZE_MB: int = 100
    FREE_TIER_MAX_MB: int = 20
    TEMP_FILE_TTL_HOURS: int = 2

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310

    OPENAI_API_KEY: str | None = None
    OLLAMA_URL: str = "http://localhost:11434"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
