"""Tests for notification scheduler"""
import pytest
from datetime import datetime, timedelta
import redis.asyncio as redis

from src.services.scheduler import NotificationScheduler
from src.models import NotificationRequest, NotificationStatus, FrontendType


@pytest.mark.asyncio
async def test_schedule_notification(redis_client):
    """Test scheduling a notification"""
    scheduler = NotificationScheduler(redis_client)

    # Create request
    request = NotificationRequest(
        user_id="user-123",
        chat_id=1153284,
        frontend=FrontendType.TELEGRAM,
        message="Test reminder",
        agent="todo",
        scheduled_for=datetime.utcnow() + timedelta(hours=1),
    )

    # Schedule
    scheduled = await scheduler.schedule_notification(request)

    # Verify
    assert scheduled.id is not None
    assert scheduled.status == NotificationStatus.PENDING
    assert scheduled.message == "Test reminder"

    # Check Redis
    score = int(scheduled.scheduled_for.timestamp())
    exists = await redis_client.zscore("notification:index", scheduled.id)
    assert exists == score


@pytest.mark.asyncio
async def test_get_due_notifications(redis_client):
    """Test getting due notifications"""
    scheduler = NotificationScheduler(redis_client)

    # Schedule notification for past (should be due)
    request = NotificationRequest(
        user_id="user-123",
        chat_id=1153284,
        frontend=FrontendType.TELEGRAM,
        message="Past reminder",
        agent="todo",
        scheduled_for=datetime.utcnow() - timedelta(minutes=1),
    )

    scheduled = await scheduler.schedule_notification(request)

    # Get due notifications
    due = await scheduler.get_due_notifications()

    # Verify
    assert len(due) == 1
    assert due[0].id == scheduled.id


@pytest.mark.asyncio
async def test_cancel_notification(redis_client):
    """Test cancelling a notification"""
    scheduler = NotificationScheduler(redis_client)

    # Schedule notification
    request = NotificationRequest(
        user_id="user-123",
        chat_id=1153284,
        frontend=FrontendType.TELEGRAM,
        message="Test reminder",
        agent="todo",
        scheduled_for=datetime.utcnow() + timedelta(hours=1),
    )

    scheduled = await scheduler.schedule_notification(request)

    # Cancel
    success = await scheduler.cancel_notification(scheduled.id)
    assert success is True

    # Verify removed from index
    exists = await redis_client.zscore("notification:index", scheduled.id)
    assert exists is None


@pytest.mark.asyncio
async def test_mark_as_sent(redis_client):
    """Test marking notification as sent"""
    scheduler = NotificationScheduler(redis_client)

    # Schedule notification
    request = NotificationRequest(
        user_id="user-123",
        chat_id=1153284,
        frontend=FrontendType.TELEGRAM,
        message="Test reminder",
        agent="todo",
        scheduled_for=datetime.utcnow() + timedelta(hours=1),
    )

    scheduled = await scheduler.schedule_notification(request)

    # Mark as sent
    await scheduler.mark_as_sent(scheduled.id)

    # Verify delivery status
    delivery_key = f"notification:delivery:{scheduled.id}"
    status = await redis_client.hget(delivery_key, "status")
    assert status.decode() == NotificationStatus.SENT.value
