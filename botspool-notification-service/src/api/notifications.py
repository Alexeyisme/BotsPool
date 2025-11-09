"""Notification API endpoints"""
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
import redis.asyncio as redis

from ..models import (
    NotificationRequest,
    NotificationResponse,
    NotificationListResponse,
    NotificationStatus,
    ScheduledNotification,
)
from ..services.scheduler import NotificationScheduler
from ..services.dispatcher import NotificationDispatcher
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_redis_client():
    """Get Redis client"""
    client = redis.from_url(settings.REDIS_URL, decode_responses=False)
    try:
        yield client
    finally:
        await client.aclose()


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key authentication"""
    if x_api_key != settings.NOTIFICATION_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


@router.post("/notifications", response_model=NotificationResponse)
async def create_notification(
    request: NotificationRequest,
    redis_client: redis.Redis = Depends(get_redis_client),
    api_key: str = Depends(verify_api_key),
):
    """
    Create and send an immediate notification.

    Args:
        request: Notification request
        redis_client: Redis client
        api_key: API key for authentication

    Returns:
        Notification response
    """
    dispatcher = NotificationDispatcher(redis_client)

    try:
        # Dispatch immediately
        success = await dispatcher.dispatch_immediate(request)

        if not success:
            raise HTTPException(
                status_code=503, detail="Failed to dispatch notification"
            )

        logger.info(
            f"Immediate notification sent to user {request.user_id}",
            extra={
                "user_id": request.user_id,
                "chat_id": request.chat_id,
                "agent": request.agent,
            },
        )

        return NotificationResponse(
            notification_id="immediate",
            status=NotificationStatus.DISPATCHED,
            timestamp=datetime.utcnow(),
        )

    finally:
        await dispatcher.close()


@router.post("/notifications/schedule", response_model=NotificationResponse)
async def schedule_notification(
    request: NotificationRequest,
    redis_client: redis.Redis = Depends(get_redis_client),
    api_key: str = Depends(verify_api_key),
):
    """
    Schedule a notification for future delivery.

    Args:
        request: Notification request with scheduled_for
        redis_client: Redis client
        api_key: API key for authentication

    Returns:
        Notification response with ID
    """
    if not request.scheduled_for:
        raise HTTPException(
            status_code=400,
            detail="scheduled_for is required for scheduled notifications",
        )

    if request.scheduled_for <= datetime.utcnow():
        raise HTTPException(
            status_code=400, detail="scheduled_for must be in the future"
        )

    scheduler = NotificationScheduler(redis_client)

    try:
        # Schedule notification
        scheduled = await scheduler.schedule_notification(request)

        logger.info(
            f"Scheduled notification {scheduled.id} for {scheduled.scheduled_for}",
            extra={
                "notification_id": scheduled.id,
                "user_id": request.user_id,
                "scheduled_for": scheduled.scheduled_for.isoformat(),
            },
        )

        return NotificationResponse(
            notification_id=scheduled.id,
            status=NotificationStatus.PENDING,
            scheduled_for=scheduled.scheduled_for,
            timestamp=datetime.utcnow(),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to schedule notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to schedule notification")


@router.delete("/notifications/{notification_id}")
async def cancel_notification(
    notification_id: str,
    redis_client: redis.Redis = Depends(get_redis_client),
    api_key: str = Depends(verify_api_key),
):
    """
    Cancel a scheduled notification.

    Args:
        notification_id: Notification UUID
        redis_client: Redis client
        api_key: API key for authentication

    Returns:
        Cancellation status
    """
    scheduler = NotificationScheduler(redis_client)

    success = await scheduler.cancel_notification(notification_id)

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    logger.info(f"Cancelled notification {notification_id}")

    return {"status": "cancelled", "notification_id": notification_id}


@router.get("/notifications/user/{user_id}", response_model=NotificationListResponse)
async def list_user_notifications(
    user_id: str,
    status: Optional[str] = None,
    redis_client: redis.Redis = Depends(get_redis_client),
    api_key: str = Depends(verify_api_key),
):
    """
    List user's scheduled notifications.

    Args:
        user_id: BotsPool user UUID
        status: Filter by status (optional)
        redis_client: Redis client
        api_key: API key for authentication

    Returns:
        List of notifications
    """
    scheduler = NotificationScheduler(redis_client)

    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = NotificationStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    notifications = await scheduler.get_user_notifications(user_id, status_filter)

    return NotificationListResponse(
        notifications=notifications, total=len(notifications)
    )


@router.get("/notifications/{notification_id}", response_model=ScheduledNotification)
async def get_notification(
    notification_id: str,
    redis_client: redis.Redis = Depends(get_redis_client),
    api_key: str = Depends(verify_api_key),
):
    """
    Get notification by ID.

    Args:
        notification_id: Notification UUID
        redis_client: Redis client
        api_key: API key for authentication

    Returns:
        Notification details
    """
    scheduler = NotificationScheduler(redis_client)

    notification = await scheduler.get_notification(notification_id)

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return notification
