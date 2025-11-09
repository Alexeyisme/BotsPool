"""Configuration management for notification service"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service configuration
    SERVICE_NAME: str = "botspool-notification-service"
    HOST: str = "0.0.0.0"
    PORT: int = 8090
    LOG_LEVEL: str = "INFO"

    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # Frontend endpoints
    TELEGRAM_BOT_URL: str = "http://localhost:8081"

    # Authentication
    NOTIFICATION_API_KEY: str = os.getenv(
        "NOTIFICATION_API_KEY", "dev-secret-key-change-in-production"
    )

    # Rate limiting
    MAX_NOTIFICATIONS_PER_HOUR: int = 10

    # Worker configuration
    WORKER_CHECK_INTERVAL_SECONDS: int = (
        10  # Check every 10 seconds for timely delivery
    )

    # Retry configuration
    MAX_DELIVERY_ATTEMPTS: int = 3
    RETRY_DELAY_SECONDS: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
