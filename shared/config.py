"""
Configuration module — Central access point for environment variables.

CRITICAL: Access ALL environment variables through this module.
NEVER use os.getenv() directly in application code.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Project
    PROJECT_NAME: str = Field(default="Zanovix CRM", description="Project name")
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment: development, staging, production",
    )

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://zanovix:changeme@postgres:5432/zanovix_crm",
        description="PostgreSQL connection string with asyncpg driver",
    )
    POSTGRES_DB: str = Field(default="zanovix_crm")
    POSTGRES_USER: str = Field(default="zanovix")
    POSTGRES_PASSWORD: str = Field(default="changeme")
    POSTGRES_HOST: str = Field(default="postgres")
    POSTGRES_PORT: int = Field(default=5432)

    # Redis
    REDIS_URL: str = Field(
        default="redis://redis:6379/0", description="Redis connection string"
    )
    REDIS_PASSWORD: str = Field(default="", description="Redis password")

    # JWT Auth
    JWT_SECRET_KEY: str = Field(
        default="change-me-in-production-min-32-chars-secret",
        description="JWT signing secret (min 32 chars in production)",
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRE_MINUTES: int = Field(default=1440, description="Token TTL in minutes (default 24h)")

    # Rate limiting
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60)
    RATE_LIMIT_MAX_REQUESTS: int = Field(default=20)

    # IP hashing (PII protection)
    IP_HASH_SALT: str = Field(
        default="change-me-random-salt",
        description="Salt for IP address hashing before storage",
    )

    # CORS
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000,http://localhost:8001",
        description="Comma-separated list of allowed CORS origins",
    )

    # Trusted proxies (for X-Forwarded-For)
    TRUSTED_PROXIES: str = Field(
        default="",
        description="Comma-separated list of trusted proxy IPs (empty = trust all)",
    )

    # Observability
    LOG_LEVEL: str = Field(default="INFO")
    SENTRY_DSN: str = Field(default="", description="Sentry DSN (empty = disabled)")

    # Seed passwords (dev defaults — override in production)
    SEED_ADMIN_PASSWORD: str = Field(default="admin123")
    SEED_CONSULTOR_PASSWORD: str = Field(default="consultor123")
    SEED_COMERCIAL_PASSWORD: str = Field(default="comercial123")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
