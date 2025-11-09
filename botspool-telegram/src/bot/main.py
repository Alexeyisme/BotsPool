"""Main bot application"""
import asyncio
import logging
import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.ext import ContextTypes
import redis.asyncio as redis
import uvicorn
from threading import Thread

from botspool_shared_utils.database import create_connection_pool, close_connection_pool
from botspool_shared_utils.redis_utils import RedisManager
from botspool_shared_utils.sessions import SessionService, SessionSettings

from ..config import Settings
from ..logging_config import setup_logging
from .state import SessionState
from ..gateway.client import GatewayClient
from ..gateway import auth as gateway_auth
from .rate_limiter import RateLimiter
from .notifications import notification_app, set_bot_instance

# Import handlers
from .handlers.start import start_handler as start_handler_impl
from .handlers.menu import (
    menu_handler as menu_handler_impl,
    callback_query_handler as callback_query_handler_impl,
)
from .handlers.status import status_handler as status_handler_impl
from .handlers.reset import reset_handler as reset_handler_impl
from .handlers.help import help_handler as help_handler_impl
from .handlers.chat import chat_handler as chat_handler_impl

settings = Settings()
logger = setup_logging(settings.LOG_LEVEL)

# Global instances
redis_client = None
state = None
gateway_client = None
rate_limiter = None
session_service = None
session_settings = SessionSettings.from_env()
db_manager = None


async def post_init(application: Application):
    """Initialize services after bot is created"""
    global redis_client, state, gateway_client, rate_limiter, session_service, db_manager

    logger.info("Initializing bot services...")

    # Connect to Redis
    redis_client = await redis.from_url(settings.REDIS_URL, decode_responses=False)
    await redis_client.ping()
    logger.info("Redis connected")

    # Initialize shared session infrastructure
    db_manager = await create_connection_pool(settings.SESSION_DATABASE_URL)
    redis_manager = RedisManager(redis_client)
    session_service = SessionService(db_manager, redis_manager, session_settings)

    # Initialize state manager
    state = SessionState(
        redis_client,
        settings.CREDENTIAL_ENCRYPTION_KEY,
        session_service,
        settings.DEFAULT_AGENT,
    )

    # Initialize Gateway client
    gateway_client = GatewayClient(settings.GATEWAY_URL, state)

    # Test Gateway connection with retries
    max_retries = 5
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.GATEWAY_URL}/health/status", timeout=10.0
                )
                response.raise_for_status()
            logger.info("Gateway connected")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                logger.warning(f"Gateway not ready, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("Failed to connect to Gateway", exc_info=True)
                raise

    # Initialize rate limiter
    rate_limiter = RateLimiter(redis_client, settings.MESSAGE_RATE_LIMIT)

    # Set bot instance for notification endpoint
    set_bot_instance(application.bot, settings)

    # Start notification server in background thread
    def run_notification_server():
        uvicorn.run(
            notification_app,
            host="0.0.0.0",
            port=settings.NOTIFICATION_PORT,
            log_level=settings.LOG_LEVEL.lower(),
        )

    notification_thread = Thread(target=run_notification_server, daemon=True)
    notification_thread.start()
    logger.info(f"Notification endpoint started on port {settings.NOTIFICATION_PORT}")

    # Set bot commands in Telegram UI
    await application.bot.set_my_commands(
        [
            ("start", "Start the bot and register"),
            ("menu", "Select AI assistant"),
            ("status", "Show subscription and usage"),
            ("reset", "Clear session and start fresh"),
            ("help", "Show help information"),
        ]
    )

    logger.info("Bot initialization complete")


async def post_shutdown(application: Application):
    """Cleanup on shutdown"""
    global redis_client, gateway_client, session_service, db_manager

    if gateway_client:
        await gateway_client.close()
    if redis_client:
        await redis_client.close()
    if session_service:
        await close_connection_pool()
        session_service = None
        db_manager = None
    logger.info("Bot shutdown complete")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error("Update caused error", exc_info=context.error)

    if update and update.effective_message:
        await update.effective_message.reply_text(
            "An unexpected error occurred. Please try again or contact support."
        )


# Wrapper functions to inject dependencies
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_handler_impl(
        update, context, state, gateway_client, gateway_auth, settings.GATEWAY_URL
    )


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await menu_handler_impl(update, context, gateway_client, state)


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await callback_query_handler_impl(update, context, state, gateway_client)


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await status_handler_impl(update, context, state, gateway_client)


async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reset_handler_impl(update, context, state)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await help_handler_impl(update, context)


async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await chat_handler_impl(update, context, state, gateway_client, rate_limiter)


def main():
    """Start the bot"""
    logger.info("Starting BotsPool Telegram Bot...")

    # Build application
    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Register handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("menu", menu_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("reset", reset_handler))
    app.add_handler(CommandHandler("help", help_handler))

    # Callback query handler for inline keyboards
    app.add_handler(CallbackQueryHandler(callback_query_handler))

    # Message handler for chat (text only, no commands)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

    # Error handler
    app.add_error_handler(error_handler)

    # Start polling
    logger.info("Bot started polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
