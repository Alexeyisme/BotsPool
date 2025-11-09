"""Notification endpoint for receiving notifications from notification service"""
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
from telegram import Bot
import httpx

from ..config import Settings


# Models
class NotificationRequest(BaseModel):
    """Incoming notification request"""

    chat_id: int
    message: str
    agent: str
    notification_type: str
    priority: str = "normal"


class NotificationResponse(BaseModel):
    """Notification delivery response"""

    status: str
    delivered_at: str


# FastAPI app for notifications
notification_app = FastAPI(title="Telegram Bot Notification Endpoint")

# Global instances (will be set from main.py)
bot_token: Optional[str] = None
settings: Optional[Settings] = None

logger = logging.getLogger(__name__)


def set_bot_instance(bot: Bot, bot_settings: Settings):
    """
    Set the bot token for sending notifications.

    Args:
        bot: Telegram Bot instance (we'll extract the token)
        bot_settings: Bot settings
    """
    global bot_token, settings
    bot_token = bot.token
    settings = bot_settings


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key from notification service"""
    if not settings:
        raise HTTPException(status_code=503, detail="Bot not initialized")

    expected_key = settings.NOTIFICATION_API_KEY
    if x_api_key != expected_key:
        logger.warning(f"Invalid API key attempt: {x_api_key}")
        raise HTTPException(status_code=403, detail="Invalid API key")

    return x_api_key


@notification_app.post("/api/v1/notify", response_model=NotificationResponse)
async def receive_notification(
    notification: NotificationRequest, api_key: str = Header(None, alias="X-API-Key")
):
    """
    Receive notification from notification service and send to Telegram user.

    Args:
        notification: Notification request
        api_key: API key for authentication

    Returns:
        Delivery confirmation
    """
    # Verify API key
    if not settings:
        raise HTTPException(status_code=503, detail="Bot not initialized")

    if api_key != settings.NOTIFICATION_API_KEY:
        logger.warning(f"Invalid API key in notification request")
        raise HTTPException(status_code=403, detail="Invalid API key")

    if not bot_token:
        raise HTTPException(status_code=503, detail="Bot not initialized")

    try:
        # Format message based on type
        icon = {"reminder": "⏰", "alert": "🔔", "info": "ℹ️", "update": "📬"}.get(
            notification.notification_type, "📬"
        )

        formatted_message = f"{icon} **{notification.agent.title()} Assistant**\n\n{notification.message}"

        # Create a new Bot instance for this request to avoid event loop conflicts
        # This bot will use the current thread's event loop
        async with httpx.AsyncClient() as http_client:
            bot = Bot(token=bot_token, request=None)
            # Use httpx directly to send message
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = await http_client.post(
                url,
                json={
                    "chat_id": notification.chat_id,
                    "text": formatted_message,
                    "parse_mode": "Markdown",
                },
            )
            response.raise_for_status()

        logger.info(
            f"Notification delivered to chat {notification.chat_id}",
            extra={
                "chat_id": notification.chat_id,
                "agent": notification.agent,
                "notification_type": notification.notification_type,
            },
        )

        return NotificationResponse(
            status="delivered", delivered_at=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(
            f"Failed to deliver notification to chat {notification.chat_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to deliver notification: {str(e)}"
        )


@notification_app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if bot_token else "not_initialized",
        "timestamp": datetime.utcnow().isoformat(),
    }
