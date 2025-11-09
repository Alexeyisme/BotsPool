"""Handler for /help command"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "🤖 BotsPool Help\n\n"
        "Commands:\n"
        "/start - Start the bot and register\n"
        "/menu - Select AI assistant\n"
        "/status - Show your subscription and usage\n"
        "/reset - Clear session and start fresh\n"
        "/help - Show this help message\n\n"
        "How to use:\n"
        "1. Select an assistant from the menu\n"
        "2. Send your message\n"
        "3. The assistant will respond\n"
        "4. Switch assistants anytime with /menu\n\n"
        "Each assistant has its own conversation context!"
    )

    await update.message.reply_text(help_text)


async def help_handler_callback(query):
    """Handle help callback from inline keyboard"""
    help_text = (
        "🤖 BotsPool Help\n\n"
        "Commands:\n"
        "/start - Start the bot and register\n"
        "/menu - Select AI assistant\n"
        "/status - Show your subscription and usage\n"
        "/reset - Clear session and start fresh\n"
        "/help - Show this help message\n\n"
        "How to use:\n"
        "1. Select an assistant from the menu\n"
        "2. Send your message\n"
        "3. The assistant will respond\n"
        "4. Switch assistants anytime with /menu\n\n"
        "Each assistant has its own conversation context!"
    )

    await query.edit_message_text(help_text)
