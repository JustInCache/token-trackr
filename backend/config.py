"""
Application Configuration
=========================
Centralized configuration management using Pydantic Settings.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: str = Field(default="change-me-in-production", min_length=16)

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/token_trackr"
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")

    # AWS
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-1"

    # Azure OpenAI
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_api_version: str = "2024-02-01"

    # Google
    google_api_key: str | None = None

    # Token Trackr
    token_trackr_url: str = "http://localhost:8000"
    token_trackr_api_key: str | None = None

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # Metrics
    metrics_enabled: bool = True
    metrics_port: int = 9090

    # Scheduler
    scheduler_enabled: bool = True
    daily_aggregation_hour: int = 2
    monthly_aggregation_day: int = 1

    # Pricing config path
    pricing_config_path: str = "config/pricing.yaml"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def database_url_sync(self) -> str:
        """Return sync database URL for Alembic migrations."""
        return str(self.database_url).replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
