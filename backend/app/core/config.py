"""
Core configuration settings for the FastAPI application.
"""

from datetime import timedelta
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Job Queue System API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Database
    database_url: str = Field(
        default="sqlite:///./data/job_queue.db",
        alias="DATABASE_URL"
    )
    
    # Security
    secret_key: str = Field(
        default="your-super-secret-jwt-key-change-this-in-production",
        alias="SECRET_KEY"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours for development
    refresh_token_expire_days: int = 7
    
    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:8080"]
    
    # API
    api_v1_prefix: str = "/api/v1"
    docs_url: Optional[str] = "/docs"
    redoc_url: Optional[str] = "/redoc"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()