"""Configuration management for Telegram bot"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Bot configuration settings"""

    # Telegram
    TELEGRAM_BOT_TOKEN: str

    # Gateway
    GATEWAY_URL: str = "http://gateway:8000"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    SESSION_DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@postgres-gateway:5432/botspool_gateway"
    )

    # Bot settings
    DEFAULT_AGENT: str = "todo"
    SESSION_TIMEOUT: int = 86400  # 24 hours
    MESSAGE_RATE_LIMIT: int = 5  # messages per minute per user

    # Health check
    HEALTH_CHECK_PORT: int = 8080

    # Notification endpoint
    NOTIFICATION_PORT: int = 8081
    NOTIFICATION_API_KEY: str = "dev-secret-key-change-in-production"
    CREDENTIAL_ENCRYPTION_KEY: str

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env.docker"
        case_sensitive = True
