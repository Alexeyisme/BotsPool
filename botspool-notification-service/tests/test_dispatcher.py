"""Tests for notification dispatcher"""
import pytest
from unittest.mock import AsyncMock, patch
import redis.asyncio as redis

from src.services.dispatcher import NotificationDispatcher
from src.models import (
    NotificationRequest,
    FrontendType,
    NotificationPriority,
    NotificationType,
)


@pytest.mark.asyncio
async def test_dispatch_immediate(redis_client):
    """Test immediate notification dispatch"""
    dispatcher = NotificationDispatcher(redis_client)

    # Mock Telegram client
    with patch.object(
        dispatcher.clients[FrontendType.TELEGRAM], "send_notification"
    ) as mock_send:
        mock_send.return_value = AsyncMock(status="delivered")

        # Create request
        request = NotificationRequest(
            user_id="user-123",
            chat_id=1153284,
            frontend=FrontendType.TELEGRAM,
            message="Test notification",
            agent="todo",
            priority=NotificationPriority.NORMAL,
            notification_type=NotificationType.INFO,
        )

        # Dispatch
        success = await dispatcher.dispatch_immediate(request)

        # Verify
        assert success is True
        mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limit_check(redis_client):
    """Test rate limiting"""
    dispatcher = NotificationDispatcher(redis_client)

    user_id = "user-123"

    # Should allow first notification
    allowed = await dispatcher._check_rate_limit(user_id)
    assert allowed is True

    # Increment to max
    for i in range(10):
        await dispatcher._increment_rate_limit(user_id)

    # Should block after max
    allowed = await dispatcher._check_rate_limit(user_id)
    assert allowed is False


@pytest.mark.asyncio
async def test_rate_limit_increment(redis_client):
    """Test rate limit counter increment"""
    dispatcher = NotificationDispatcher(redis_client)

    user_id = "user-123"

    # Increment
    await dispatcher._increment_rate_limit(user_id)

    # Check count
    key = f"notification:ratelimit:{user_id}"
    count = await redis_client.get(key)
    assert int(count) == 1

    # Check TTL is set
    ttl = await redis_client.ttl(key)
    assert ttl > 0
