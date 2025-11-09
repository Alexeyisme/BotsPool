"""Handler for chat messages"""
import logging
import httpx
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import NetworkError
from ...models import GraphUnavailableError, AuthRefreshError

logger = logging.getLogger(__name__)


async def chat_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state,
    gateway_client,
    rate_limiter,
):
    """Handle text messages - route to active agent"""

    # Only allow private chats
    if update.effective_chat.type != "private":
        return

    chat_id = update.effective_chat.id
    telegram_user_id = update.effective_user.id
    message_text = update.message.text

    # Check rate limit
    if not await rate_limiter.check_rate_limit(telegram_user_id):
        remaining_time = await rate_limiter.get_remaining_time(telegram_user_id)
        await update.message.reply_text(
            f"⏳ Please slow down! Try again in {remaining_time} seconds."
        )
        return

    # Check if user has active session
    token = await state.get_token(chat_id)
    if not token:
        await update.message.reply_text("Please start the bot first with /start")
        return

    # Get active agent
    active_agent = await state.get_active_agent(chat_id)

    # Show typing indicator (ignore network issues)
    try:
        await update.message.chat.send_action("typing")
    except NetworkError:
        logger.warning("Failed to send typing indicator for chat %s", chat_id)

    try:
        # Send to Gateway
        response = await gateway_client.send_message(
            chat_id=chat_id,
            agent=active_agent,
            message=message_text,
            telegram_user_id=telegram_user_id,
        )

        # Send response
        await update.message.reply_text(response["response"])

        # Refresh session activity
        await state.refresh_activity(chat_id)

        logger.info(
            "Message processed",
            extra={
                "chat_id": chat_id,
                "agent": active_agent,
                "tokens_used": response.get("metadata", {}).get("tokens_used"),
            },
        )

    except GraphUnavailableError as e:
        await update.message.reply_text(
            f"The {active_agent} assistant is temporarily unavailable. 😔\n"
            f"Please try another assistant or try again later.\n\n"
            f"Use /menu to select a different assistant."
        )
        logger.warning("Graph unavailable", extra={"agent": active_agent})

    except AuthRefreshError:
        await update.message.reply_text(
            "Your session expired. Please send /start to reconnect."
        )
        logger.info(
            "Prompted user %s to restart session after auth refresh failure", chat_id
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            await update.message.reply_text(
                "You've reached your rate limit. Please wait a moment and try again."
            )
        elif e.response.status_code == 403:
            await update.message.reply_text(
                "You don't have access to this assistant. Please upgrade your subscription."
            )
        else:
            await update.message.reply_text(
                "Sorry, something went wrong. Please try again later."
            )
        logger.error(
            "Gateway error",
            exc_info=True,
            extra={"status_code": e.response.status_code},
        )

    except Exception as e:
        await update.message.reply_text(
            "Sorry, I encountered an error processing your message. Please try again."
        )
        logger.error("Chat handler error", exc_info=True)
