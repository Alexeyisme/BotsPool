"""Pytest configuration and fixtures"""
import pytest
import redis.asyncio as redis
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.main import app
from src.config import Settings


@pytest.fixture
def test_settings():
    """Test settings"""
    return Settings(
        REDIS_URL="redis://localhost:6379/15",  # Use test database
        TELEGRAM_BOT_URL="http://localhost:8081",
        NOTIFICATION_API_KEY="test-api-key",
        LOG_LEVEL="DEBUG",
    )


@pytest.fixture
async def redis_client():
    """Redis client for tests"""
    client = redis.from_url("redis://localhost:6379/15", decode_responses=False)
    yield client
    # Cleanup
    await client.flushdb()
    await client.aclose()


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Async HTTP client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_notification_request():
    """Sample notification request"""
    return {
        "user_id": "user-uuid-123",
        "chat_id": 1153284,
        "frontend": "telegram",
        "message": "Test notification",
        "agent": "todo",
        "priority": "normal",
        "notification_type": "info",
    }
