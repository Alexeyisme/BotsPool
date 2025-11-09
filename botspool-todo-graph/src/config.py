"""
Configuration for BotsPool ToDo Graph Service
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application settings
    app_name: str = "BotsPool ToDo Graph"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Database settings
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5433/botspool_todograph"
    )

    # Redis settings
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 10
    redis_decode_responses: bool = True

    # OpenAI settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.0
    openai_mock_mode: bool = True  # Use mock OpenAI responses for testing

    # LangSmith settings
    langsmith_api_key: str = ""
    langsmith_tracing_v2: Optional[str] = None

    # Core Gateway settings
    gateway_url: str = "http://localhost:8000"
    gateway_register_endpoint: str = "/api/v1/graphs/register"
    gateway_health_endpoint: str = "/health"

    # Graph settings
    graph_type: str = "todo"
    graph_name: str = "task_maistro"
    graph_version: str = "1.0.0"
    graph_capacity: int = 100
    graph_endpoint: str = "http://localhost:8001"
    instance_id: str = "todo-001"

    # Memory settings
    memory_namespace: str = "todo_memory"
    memory_ttl: int = 86400  # 24 hours

    # Health check settings
    health_check_interval: int = 30
    health_check_timeout: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings."""
    global _settings

    if _settings is None:
        _settings = Settings()

    return _settings
