"""Notification dispatcher - routes notifications to frontends"""
import logging
from typing import Dict
import redis.asyncio as redis

from botspool_shared_utils.redis_utils import (
    check_rate_limit_count,
    increment_rate_limit_counter,
)

from ..models import (
    ScheduledNotification,
    BotNotificationRequest,
    FrontendType,
    NotificationRequest,
)
from ..clients.telegram_client import TelegramClient
from ..clients.base_client import BaseFrontendClient
from ..config import settings

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Dispatches notifications to appropriate frontend"""

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize dispatcher.

        Args:
            redis_client: Async Redis client
        """
        self.redis = redis_client
        self.clients: Dict[FrontendType, BaseFrontendClient] = {
            FrontendType.TELEGRAM: TelegramClient()
        }

    async def dispatch_immediate(self, request: NotificationRequest) -> bool:
        """
        Dispatch notification immediately.

        Args:
            request: Notification request

        Returns:
            True if successfully dispatched
        """
        # Check rate limit
        if not await self._check_rate_limit(request.user_id):
            logger.warning(
                f"Rate limit exceeded for user {request.user_id}",
                extra={"user_id": request.user_id},
            )
            return False

        # Get appropriate client
        client = self.clients.get(request.frontend)
        if not client:
            logger.error(f"No client available for frontend {request.frontend}")
            return False

        # Create bot notification request
        bot_request = BotNotificationRequest(
            chat_id=request.chat_id,
            message=request.message,
            agent=request.agent,
            notification_type=request.notification_type,
            priority=request.priority,
        )

        try:
            # Send notification
            response = await client.send_notification(bot_request)

            # Update rate limit
            await self._increment_rate_limit(request.user_id)

            logger.info(
                f"Successfully dispatched notification to {request.frontend}",
                extra={
                    "user_id": request.user_id,
                    "chat_id": request.chat_id,
                    "frontend": request.frontend.value,
                },
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to dispatch notification: {e}",
                exc_info=True,
                extra={"user_id": request.user_id, "frontend": request.frontend.value},
            )
            return False

    async def dispatch_scheduled(self, notification: ScheduledNotification) -> bool:
        """
        Dispatch a scheduled notification.

        Args:
            notification: Scheduled notification

        Returns:
            True if successfully dispatched
        """
        # Check rate limit
        if not await self._check_rate_limit(notification.user_id):
            logger.warning(
                f"Rate limit exceeded for user {notification.user_id}",
                extra={"user_id": notification.user_id},
            )
            # Will retry later
            return False

        # Get appropriate client
        client = self.clients.get(notification.frontend)
        if not client:
            logger.error(f"No client available for frontend {notification.frontend}")
            return False

        # Create bot notification request
        bot_request = BotNotificationRequest(
            chat_id=notification.chat_id,
            message=notification.message,
            agent=notification.agent,
            notification_type=notification.notification_type,
            priority=notification.priority,
        )

        try:
            # Send notification
            response = await client.send_notification(bot_request)

            # Update rate limit
            await self._increment_rate_limit(notification.user_id)

            logger.info(
                f"Successfully dispatched scheduled notification {notification.id}",
                extra={
                    "notification_id": notification.id,
                    "user_id": notification.user_id,
                    "frontend": notification.frontend.value,
                },
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to dispatch scheduled notification {notification.id}: {e}",
                exc_info=True,
                extra={
                    "notification_id": notification.id,
                    "user_id": notification.user_id,
                },
            )
            return False

    async def _check_rate_limit(self, user_id: str) -> bool:
        """
        Check if user has exceeded rate limit.

        Args:
            user_id: BotsPool user UUID

        Returns:
            True if within limit
        """
        key = f"notification:ratelimit:{user_id}"
        return await check_rate_limit_count(
            self.redis, key, settings.MAX_NOTIFICATIONS_PER_HOUR
        )

    async def _increment_rate_limit(self, user_id: str):
        """
        Increment user's rate limit counter.

        Args:
            user_id: BotsPool user UUID
        """
        key = f"notification:ratelimit:{user_id}"
        await increment_rate_limit_counter(self.redis, key, 3600)  # 1 hour window

    async def close(self):
        """Close all client connections"""
        for client in self.clients.values():
            if hasattr(client, "close"):
                await client.close()
