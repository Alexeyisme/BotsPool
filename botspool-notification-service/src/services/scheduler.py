"""Redis-based notification scheduler"""
import json
import time
import uuid
import logging
from datetime import datetime
from typing import Optional, List
import redis.asyncio as redis

from ..models import ScheduledNotification, NotificationStatus, NotificationRequest
from ..config import settings

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Manages scheduled notifications in Redis"""

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize scheduler.

        Args:
            redis_client: Async Redis client
        """
        self.redis = redis_client

    async def schedule_notification(
        self, request: NotificationRequest
    ) -> ScheduledNotification:
        """
        Schedule a notification for future delivery.

        Args:
            request: Notification request with scheduled_for datetime

        Returns:
            Created scheduled notification
        """
        if not request.scheduled_for:
            raise ValueError(
                "scheduled_for must be provided for scheduled notifications"
            )

        # Generate unique ID
        notification_id = str(uuid.uuid4())

        # Create scheduled notification
        scheduled = ScheduledNotification(
            id=notification_id,
            user_id=request.user_id,
            chat_id=request.chat_id,
            frontend=request.frontend,
            message=request.message,
            agent=request.agent,
            priority=request.priority,
            notification_type=request.notification_type,
            status=NotificationStatus.PENDING,
            created_at=datetime.utcnow(),
            scheduled_for=request.scheduled_for,
            metadata=request.metadata,
        )

        # Calculate timestamp
        timestamp = int(scheduled.scheduled_for.timestamp())

        # Calculate TTL (time until scheduled + 1 hour buffer)
        ttl_seconds = (
            int((scheduled.scheduled_for - datetime.utcnow()).total_seconds()) + 3600
        )
        if ttl_seconds < 60:
            ttl_seconds = 60  # Minimum 1 minute

        # Store notification data
        notification_key = f"notification:scheduled:{timestamp}:{notification_id}"
        await self.redis.set(
            notification_key, scheduled.model_dump_json(), ex=ttl_seconds
        )

        # Add to sorted set for time-based queries
        await self.redis.zadd("notification:index", {notification_id: timestamp})

        # Add to user's reminder list
        user_key = f"notification:user:{request.user_id}:reminders"
        await self.redis.sadd(user_key, notification_id)
        await self.redis.expire(user_key, ttl_seconds)

        logger.info(
            f"Scheduled notification {notification_id} for {scheduled.scheduled_for}",
            extra={
                "notification_id": notification_id,
                "user_id": request.user_id,
                "scheduled_for": scheduled.scheduled_for.isoformat(),
            },
        )

        return scheduled

    async def get_due_notifications(self) -> List[ScheduledNotification]:
        """
        Get notifications that are due for delivery.

        Returns:
            List of due notifications
        """
        current_time = int(time.time())

        # Get due notification IDs from sorted set
        due_ids = await self.redis.zrangebyscore("notification:index", 0, current_time)

        if not due_ids:
            return []

        notifications = []
        for notification_id in due_ids:
            if isinstance(notification_id, bytes):
                notification_id = notification_id.decode()

            # Get notification data
            notification = await self.get_notification(notification_id)
            if notification and notification.status == NotificationStatus.PENDING:
                notifications.append(notification)

        return notifications

    async def get_notification(
        self, notification_id: str
    ) -> Optional[ScheduledNotification]:
        """
        Get notification by ID.

        Args:
            notification_id: Notification UUID

        Returns:
            Scheduled notification or None
        """
        # Search for notification key (we don't know timestamp)
        pattern = f"notification:scheduled:*:{notification_id}"
        async for key in self.redis.scan_iter(match=pattern):
            data = await self.redis.get(key)
            if data:
                if isinstance(data, bytes):
                    data = data.decode()
                return ScheduledNotification.model_validate_json(data)

        return None

    async def cancel_notification(self, notification_id: str) -> bool:
        """
        Cancel a scheduled notification.

        Args:
            notification_id: Notification UUID

        Returns:
            True if cancelled, False if not found
        """
        notification = await self.get_notification(notification_id)
        if not notification:
            return False

        # Update status
        notification.status = NotificationStatus.CANCELLED

        # Update in Redis
        timestamp = int(notification.scheduled_for.timestamp())
        notification_key = f"notification:scheduled:{timestamp}:{notification_id}"
        await self.redis.set(notification_key, notification.model_dump_json())

        # Remove from sorted set
        await self.redis.zrem("notification:index", notification_id)

        # Remove from user's reminders
        user_key = f"notification:user:{notification.user_id}:reminders"
        await self.redis.srem(user_key, notification_id)

        logger.info(f"Cancelled notification {notification_id}")

        return True

    async def mark_as_sent(self, notification_id: str):
        """
        Mark notification as sent.

        Args:
            notification_id: Notification UUID
        """
        notification = await self.get_notification(notification_id)
        if not notification:
            return

        # Update status
        notification.status = NotificationStatus.SENT

        # Remove from sorted set
        await self.redis.zrem("notification:index", notification_id)

        # Store delivery status
        delivery_key = f"notification:delivery:{notification_id}"
        await self.redis.hset(
            delivery_key,
            mapping={
                "status": NotificationStatus.SENT.value,
                "delivered_at": datetime.utcnow().isoformat(),
                "attempts": str(notification.attempts + 1),
            },
        )
        await self.redis.expire(delivery_key, 86400)  # Keep for 24 hours

        logger.info(f"Marked notification {notification_id} as sent")

    async def mark_as_failed(self, notification_id: str, error: str):
        """
        Mark notification as failed.

        Args:
            notification_id: Notification UUID
            error: Error message
        """
        notification = await self.get_notification(notification_id)
        if not notification:
            return

        # Update attempts
        notification.attempts += 1
        notification.last_attempt = datetime.utcnow()

        # Check if max attempts reached
        if notification.attempts >= settings.MAX_DELIVERY_ATTEMPTS:
            notification.status = NotificationStatus.FAILED
            # Remove from sorted set (won't retry)
            await self.redis.zrem("notification:index", notification_id)
            logger.error(
                f"Notification {notification_id} failed after {notification.attempts} attempts"
            )

        # Update in Redis
        timestamp = int(notification.scheduled_for.timestamp())
        notification_key = f"notification:scheduled:{timestamp}:{notification_id}"
        await self.redis.set(notification_key, notification.model_dump_json())

        # Store delivery status
        delivery_key = f"notification:delivery:{notification_id}"
        await self.redis.hset(
            delivery_key,
            mapping={
                "status": notification.status.value,
                "attempts": str(notification.attempts),
                "last_error": error,
            },
        )
        await self.redis.expire(delivery_key, 86400)

    async def get_user_notifications(
        self, user_id: str, status: Optional[NotificationStatus] = None
    ) -> List[ScheduledNotification]:
        """
        Get user's scheduled notifications.

        Args:
            user_id: BotsPool user UUID
            status: Filter by status (optional)

        Returns:
            List of notifications
        """
        user_key = f"notification:user:{user_id}:reminders"
        notification_ids = await self.redis.smembers(user_key)

        if not notification_ids:
            return []

        notifications = []
        for notification_id in notification_ids:
            if isinstance(notification_id, bytes):
                notification_id = notification_id.decode()

            notification = await self.get_notification(notification_id)
            if notification:
                if status is None or notification.status == status:
                    notifications.append(notification)

        # Sort by scheduled time
        notifications.sort(key=lambda n: n.scheduled_for)

        return notifications
