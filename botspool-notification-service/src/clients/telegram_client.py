"""Telegram bot client for sending notifications"""
import logging
import httpx
from datetime import datetime

from .base_client import BaseFrontendClient
from ..models import BotNotificationRequest, BotNotificationResponse
from ..config import settings

logger = logging.getLogger(__name__)


class TelegramClient(BaseFrontendClient):
    """Client for sending notifications to Telegram bot"""

    def __init__(self, bot_url: str = None, api_key: str = None):
        """
        Initialize Telegram client.

        Args:
            bot_url: Telegram bot notification endpoint URL
            api_key: API key for authentication
        """
        self.bot_url = bot_url or settings.TELEGRAM_BOT_URL
        self.api_key = api_key or settings.NOTIFICATION_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)

    async def send_notification(
        self, request: BotNotificationRequest
    ) -> BotNotificationResponse:
        """
        Send notification to Telegram bot.

        Args:
            request: Notification request

        Returns:
            Delivery response

        Raises:
            httpx.HTTPError: If delivery fails
        """
        endpoint = f"{self.bot_url}/api/v1/notify"

        headers = {"Content-Type": "application/json", "X-API-Key": self.api_key}

        payload = request.model_dump()

        logger.info(
            f"Sending notification to Telegram chat {request.chat_id}",
            extra={
                "chat_id": request.chat_id,
                "agent": request.agent,
                "notification_type": request.notification_type,
            },
        )

        try:
            response = await self.client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()
            return BotNotificationResponse(
                status=data.get("status", "delivered"),
                delivered_at=datetime.fromisoformat(data["delivered_at"])
                if "delivered_at" in data
                else datetime.utcnow(),
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to send notification: HTTP {e.response.status_code}",
                extra={
                    "status_code": e.response.status_code,
                    "response": e.response.text,
                },
            )
            raise

        except httpx.RequestError as e:
            logger.error(f"Failed to send notification: {e}", exc_info=True)
            raise

    async def health_check(self) -> bool:
        """
        Check if Telegram bot is healthy.

        Returns:
            True if healthy
        """
        try:
            health_endpoint = f"{self.bot_url}/health"
            response = await self.client.get(health_endpoint, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Telegram bot health check failed: {e}")
            return False

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
