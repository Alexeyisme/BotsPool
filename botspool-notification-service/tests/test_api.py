"""Tests for notification API endpoints"""
from datetime import datetime, timedelta

import fakeredis.aioredis as fakeredis
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.config import settings
from src.api.notifications import get_redis_client
from src.clients.telegram_client import TelegramClient


TEST_API_KEY = "test-api-key"


@pytest.fixture(autouse=True)
def _mock_dependencies(monkeypatch):
    """Ensure tests do not hit real Redis or Telegram endpoints."""

    fake_redis = fakeredis.FakeRedis(decode_responses=False)

    async def fake_get_redis():
        yield fake_redis

    app.dependency_overrides[get_redis_client] = fake_get_redis

    async def fake_send_notification(
        self, request
    ):  # pragma: no cover - patched behavior
        return {"ok": True}

    monkeypatch.setattr(
        TelegramClient, "send_notification", fake_send_notification, raising=False
    )

    original_api_key = settings.NOTIFICATION_API_KEY
    original_redis_url = settings.REDIS_URL

    settings.NOTIFICATION_API_KEY = TEST_API_KEY
    settings.REDIS_URL = "redis://localhost:6379/15"

    try:
        yield
    finally:
        settings.NOTIFICATION_API_KEY = original_api_key
        settings.REDIS_URL = original_redis_url
        app.dependency_overrides.pop(get_redis_client, None)


client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data


def test_create_immediate_notification_without_auth():
    """Test creating notification without API key"""
    response = client.post(
        "/api/v1/notifications",
        json={
            "user_id": "user-123",
            "chat_id": 1153284,
            "frontend": "telegram",
            "message": "Test",
            "agent": "todo",
        },
    )
    assert response.status_code == 403


def test_create_immediate_notification_with_auth():
    """Test creating notification with API key"""
    headers = {"X-API-Key": TEST_API_KEY}

    response = client.post(
        "/api/v1/notifications",
        headers=headers,
        json={
            "user_id": "user-123",
            "chat_id": 1153284,
            "frontend": "telegram",
            "message": "Test notification",
            "agent": "todo",
            "priority": "normal",
            "notification_type": "info",
        },
    )

    assert response.status_code == 200


def test_schedule_notification():
    """Test scheduling a notification"""
    headers = {"X-API-Key": TEST_API_KEY}

    scheduled_time = datetime.utcnow() + timedelta(hours=1)

    response = client.post(
        "/api/v1/notifications/schedule",
        headers=headers,
        json={
            "user_id": "user-123",
            "chat_id": 1153284,
            "frontend": "telegram",
            "message": "Test reminder",
            "agent": "todo",
            "notification_type": "reminder",
            "scheduled_for": scheduled_time.isoformat(),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "notification_id" in data
    assert data["status"] == "pending"


def test_schedule_notification_past_time():
    """Test scheduling notification for past time"""
    headers = {"X-API-Key": TEST_API_KEY}

    past_time = datetime.utcnow() - timedelta(hours=1)

    response = client.post(
        "/api/v1/notifications/schedule",
        headers=headers,
        json={
            "user_id": "user-123",
            "chat_id": 1153284,
            "frontend": "telegram",
            "message": "Test reminder",
            "agent": "todo",
            "scheduled_for": past_time.isoformat(),
        },
    )

    assert response.status_code == 400
