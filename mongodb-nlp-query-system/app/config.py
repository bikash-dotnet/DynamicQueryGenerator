"""
Application configuration management using Pydantic Settings
"""

from typing import List, Optional, Literal
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # MongoDB Configuration
    MONGODB_URL: str = Field(default="mongodb://localhost:27017")
    DATABASE_NAME: str = Field(default="nlp_query_system")
    MONGODB_MAX_CONNECTIONS: int = Field(default=50)
    MONGODB_MIN_CONNECTIONS: int = Field(default=10)
    
    # Schema Configuration
    SCHEMA_PATH: Path = Field(default=Path("./schemas"))
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    API_KEY: Optional[str] = Field(default=None)
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:8000"])
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_PER_IP: int = Field(default=60)
    
    # Query Configuration
    DEFAULT_QUERY_LIMIT: int = Field(default=5)
    QUERY_TIMEOUT_SECONDS: int = Field(default=30)
    MAX_EXPORT_SIZE_MB: int = Field(default=50)
    
    # Cache Configuration
    CACHE_TYPE: Literal["memory", "redis"] = Field(default="memory")
    REDIS_URL: Optional[str] = Field(default=None)
    CACHE_TTL_SECONDS: int = Field(default=3600)
    
    # NLP Configuration
    NLP_ENGINE: Literal["spacy", "google_adk"] = Field(default="spacy")
    GOOGLE_API_KEY: Optional[str] = Field(default=None)
    SPACY_MODEL: str = Field(default="en_core_web_md")
    
    # Email Configuration
    SMTP_HOST: Optional[str] = Field(default=None)
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    EMAIL_FROM: Optional[str] = Field(default=None)
    EMAIL_REPLY_TO: Optional[str] = Field(default=None)
    SENDGRID_API_KEY: Optional[str] = Field(default=None)
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: Literal["json", "text"] = Field(default="json")
    LOG_FILE: Path = Field(default=Path("logs/app.log"))
    
    # Security
    ENABLE_API_KEY_AUTH: bool = Field(default=False)
    ENABLE_RATE_LIMITING: bool = Field(default=True)
    MAX_QUERY_LENGTH: int = Field(default=1000)
    MAX_RESULTS: int = Field(default=10000)
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("SCHEMA_PATH", mode="before")
    @classmethod
    def validate_schema_path(cls, v):
        """Ensure schema path exists"""
        path = Path(v)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return path
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Create singleton instance
settings = Settings()


def validate_config() -> None:
    """Validate critical configuration on startup"""
    errors = []
    
    # Check schema path is readable
    if not settings.SCHEMA_PATH.exists():
        errors.append(f"Schema path does not exist: {settings.SCHEMA_PATH}")
    
    # Check NLP engine configuration
    if settings.NLP_ENGINE == "google_adk" and not settings.GOOGLE_API_KEY:
        errors.append("GOOGLE_API_KEY required when using Google ADK")
    
    # Check email configuration if needed
    if settings.SMTP_HOST and not settings.SMTP_USER:
        errors.append("SMTP_USER required when SMTP_HOST is set")
    
    if errors:
        raise ValueError(f"Configuration errors: {'; '.join(errors)}")