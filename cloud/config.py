import os
from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    database_url: str = "mysql+pymysql://username:password@localhost:3306/security_camera_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "security-camera-storage"
    
    # OpenAI
    openai_api_key: str = ""
    
    # JWT
    jwt_secret_key: str = "your_very_secure_secret_key_here"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # API Keys
    pi_api_key: str = ""
    
    # Application
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    
    # File retention
    file_retention_days: int = 7
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Notifications
    push_notification_key: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
