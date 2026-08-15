"""Runtime configuration loaded from environment variables.

Secrets deliberately have no committed values.  A development-only JWT key is
generated for a process when one is not supplied, so local startup is safe and
tokens never survive a restart by accident.
"""

import secrets
from pathlib import Path
from typing import List

from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./security_camera.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AWS
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "security-camera-storage"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"

    # JWT
    jwt_secret_key: str = secrets.token_urlsafe(48)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # Application
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # File retention
    file_retention_days: int = 7

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, value):
        """Accept JSON lists (Pydantic default) or a simple comma-separated env var."""
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    class Config:
        env_file = str(Path(__file__).with_name(".env"))
        case_sensitive = False


# Global settings instance
settings = Settings()
