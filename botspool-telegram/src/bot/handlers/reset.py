"""Handler for /reset command"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, state):
    """Handle /reset command - clear session and restart"""
    chat_id = update.effective_chat.id

    await state.clear_session(chat_id, preserve_credentials=True)

    await update.message.reply_text(
        "Your session has been cleared! 🔄\n\n" "Send /start to begin again."
    )

    logger.info("User reset session", extra={"chat_id": chat_id})
