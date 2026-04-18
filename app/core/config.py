import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "PDF Toolkit"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/pdf_toolkit"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Storage
    STORAGE_TYPE: str = "local"  # local, s3, minio
    STORAGE_BUCKET: str = "pdf-toolkit"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # File limits
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    MAX_FILES_PER_REQUEST: int = 10
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # ClamAV
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310
    
    class Config:
        env_file = ".env"

settings = Settings()