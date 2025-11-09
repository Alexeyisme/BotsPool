"""Handler for /menu command and callback queries"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from ..keyboards import build_main_menu_keyboard

logger = logging.getLogger(__name__)


async def menu_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, gateway_client, state
):
    """Handle /menu command - show agent selection"""
    chat_id = update.effective_chat.id

    keyboard = await build_main_menu_keyboard(gateway_client, chat_id)
    await update.message.reply_text("Select an AI assistant:", reply_markup=keyboard)


async def callback_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state, gateway_client
):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    if data.startswith("select_graph:"):
        agent = data.split(":")[1]
        await state.set_active_agent(chat_id, agent)

        agent_names = {
            "todo": "📝 ToDo Assistant",
            "email": "📧 Email Assistant",
            "calendar": "📅 Calendar Assistant",
            "document": "📄 Document Assistant",
            "code": "💻 Code Assistant",
            "research": "🔍 Research Assistant",
        }

        await query.edit_message_text(
            f"Switched to {agent_names.get(agent, agent)}!\n\n"
            f"Send me a message and I'll help you with {agent} tasks."
        )

        logger.info("User switched agent", extra={"chat_id": chat_id, "agent": agent})

    elif data == "show_status":
        # Import here to avoid circular import
        from .status import status_handler_callback

        await status_handler_callback(query, state, gateway_client)

    elif data == "show_help":
        # Import here to avoid circular import
        from .help import help_handler_callback

        await help_handler_callback(query)
