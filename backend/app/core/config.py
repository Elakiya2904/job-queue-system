"""
Core configuration settings for the FastAPI application.
"""

import os
from datetime import timedelta
from typing import Optional, Literal
from pydantic_settings import BaseSettings
from pydantic import Field, computed_field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Job Queue System API"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    
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
    
    # Queue Configuration
    queue_type: Literal["internal", "sqs"] = Field(default="internal", alias="QUEUE_TYPE")
    
    # AWS Configuration (only used when queue_type = "sqs")
    aws_region: Optional[str] = Field(default=None, alias="AWS_REGION")
    sqs_queue_url: Optional[str] = Field(default=None, alias="SQS_QUEUE_URL")
    sqs_dlq_url: Optional[str] = Field(default=None, alias="SQS_DLQ_URL")
    
    # Lambda Configuration
    is_lambda: bool = Field(default=False, alias="IS_LAMBDA")
    lambda_task_root: Optional[str] = Field(default=None, alias="LAMBDA_TASK_ROOT")
    
    # CORS
    allowed_origins: list[str] = [
        "http://localhost:3000", 
        "http://localhost:3001", 
        "http://localhost:8080",
        "https://*.vercel.app",
        "https://*.amazonaws.com"
    ]
    
    # API
    api_v1_prefix: str = "/api/v1"
    
    @computed_field
    @property
    def docs_url(self) -> Optional[str]:
        """Only enable docs in development and staging."""
        return "/docs" if self.environment in ["development", "staging"] else None
    
    @computed_field
    @property
    def redoc_url(self) -> Optional[str]:
        """Only enable redoc in development and staging."""
        return "/redoc" if self.environment in ["development", "staging"] else None
    
    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"
    
    @computed_field
    @property
    def is_aws_environment(self) -> bool:
        """Check if running in AWS (staging or production)."""
        return self.environment in ["staging", "production"] or self.is_lambda
    
    @computed_field
    @property
    def use_sqs(self) -> bool:
        """Check if SQS should be used for queuing."""
        return self.queue_type == "sqs" and self.sqs_queue_url is not None
    
    def get_database_url(self) -> str:
        """Get database URL with environment-specific defaults."""
        if self.is_lambda and "RDS_DATABASE_URL" in os.environ:
            # In Lambda, use the RDS URL from environment
            return os.environ["RDS_DATABASE_URL"]
        return self.database_url
        
    class Config:
        # Load environment-specific .env files
        env_file = [".env", f".env.{os.getenv('ENVIRONMENT', 'development')}"]
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()