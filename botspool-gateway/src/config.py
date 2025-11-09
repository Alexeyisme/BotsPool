"""
Configuration management for BotsPool Gateway

This module provides centralized configuration using Pydantic Settings,
loading from environment variables and .env files.
"""

from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses Pydantic Settings for validation and type safety.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="allow"
    )

    # Application Settings
    app_name: str = Field(default="BotsPool Gateway", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/botspool_dev",
        description="Database connection URL",
    )
    database_pool_size: int = Field(
        default=20, description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=10, description="Database max overflow connections"
    )
    database_pool_timeout: int = Field(default=30, description="Database pool timeout")
    database_pool_recycle: int = Field(
        default=3600, description="Database pool recycle time"
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    redis_max_connections: int = Field(default=50, description="Redis max connections")
    redis_decode_responses: bool = Field(
        default=True, description="Redis decode responses"
    )

    # JWT Configuration
    jwt_algorithm: str = Field(default="RS256", description="JWT algorithm")
    jwt_access_token_expiry: int = Field(
        default=3600, description="Access token expiry (seconds)"
    )
    jwt_refresh_token_expiry: int = Field(
        default=2592000, description="Refresh token expiry (seconds)"
    )
    jwt_issuer: str = Field(default="botspool.ai", description="JWT issuer")
    jwt_audience: str = Field(default="botspool-api", description="JWT audience")
    jwt_private_key: Optional[str] = Field(
        default=None, description="JWT private key (PEM format)"
    )
    jwt_public_key: Optional[str] = Field(
        default=None, description="JWT public key (PEM format)"
    )

    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins",
    )
    cors_allow_credentials: bool = Field(
        default=True, description="CORS allow credentials"
    )
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="CORS allowed methods",
    )
    cors_allow_headers: List[str] = Field(
        default=["*"], description="CORS allowed headers"
    )

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(
        default=60, description="Rate limit per minute"
    )
    rate_limit_requests_per_hour: int = Field(
        default=1000, description="Rate limit per hour"
    )

    # Graph Service Configuration
    graph_request_timeout: int = Field(
        default=30, description="Graph request timeout (seconds)"
    )
    graph_heartbeat_interval: int = Field(
        default=60, description="Graph heartbeat interval (seconds)"
    )
    graph_stale_threshold: int = Field(
        default=180, description="Graph stale threshold (seconds)"
    )

    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Metrics endpoint port")

    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["development", "staging", "production"]
        if v.lower() not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v.lower()

    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v_upper

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def get_database_config(self) -> dict:
        """Get database configuration as dictionary."""
        return {
            "url": self.database_url,
            "pool_size": self.database_pool_size,
            "max_overflow": self.database_max_overflow,
            "pool_timeout": self.database_pool_timeout,
            "pool_recycle": self.database_pool_recycle,
        }

    def get_redis_config(self) -> dict:
        """Get Redis configuration as dictionary."""
        return {
            "url": self.redis_url,
            "max_connections": self.redis_max_connections,
            "decode_responses": self.redis_decode_responses,
        }

    def get_jwt_config(self) -> dict:
        """Get JWT configuration as dictionary."""
        return {
            "algorithm": self.jwt_algorithm,
            "access_token_expiry": self.jwt_access_token_expiry,
            "refresh_token_expiry": self.jwt_refresh_token_expiry,
            "issuer": self.jwt_issuer,
            "audience": self.jwt_audience,
            "private_key": self.jwt_private_key,
            "public_key": self.jwt_public_key,
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance.

    Returns:
        Settings: Application settings
    """
    global _settings

    if _settings is None:
        _settings = Settings()

    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment.

    Useful for testing or dynamic configuration updates.

    Returns:
        Settings: Reloaded settings
    """
    global _settings
    _settings = Settings()
    return _settings
