"""Handler for /status command"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def status_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state, gateway_client
):
    """Handle /status command - show subscription and usage"""
    chat_id = update.effective_chat.id

    try:
        # Get current agent
        active_agent = await state.get_active_agent(chat_id)

        # Get subscription status
        status = await gateway_client.get_subscription_status(chat_id)

        subscription = status["subscription"]
        usage = status["usage"]

        status_text = (
            f"📊 Your Status\n\n"
            f"🤖 Current Assistant: {active_agent.title()}\n\n"
            f"📋 Subscription: {subscription['tier'].title()}\n"
            f"📈 Usage Today: {usage['current_usage']}/{usage['daily_limit']}\n"
            f"⏰ Resets: {usage.get('reset_time', 'Unknown')}\n\n"
            f"✅ Available Assistants:\n"
        )

        for graph in subscription.get("allowed_graphs", []):
            status_text += f"  • {graph.title()}\n"

        await update.message.reply_text(status_text)

    except Exception as e:
        logger.error("Failed to get status", exc_info=True)

        # Check if it's a 404 (endpoint not implemented)
        error_msg = str(e)
        if "404" in error_msg:
            await update.message.reply_text(
                "📊 Status Information\n\n"
                "🤖 Current Assistant: "
                + (await state.get_active_agent(chat_id)).title()
                + "\n\n"
                "ℹ️ The subscription system is being set up.\n"
                "For now, you have access to the ToDo Assistant!\n\n"
                "Full status tracking coming soon! 🚀"
            )
        else:
            await update.message.reply_text(
                "Sorry, I couldn't retrieve your status. Please try again later."
            )


async def status_handler_callback(query, state, gateway_client):
    """Handle status callback from inline keyboard"""
    chat_id = query.message.chat_id

    try:
        # Get current agent
        active_agent = await state.get_active_agent(chat_id)

        # Get subscription status
        status = await gateway_client.get_subscription_status(chat_id)

        subscription = status["subscription"]
        usage = status["usage"]

        status_text = (
            f"📊 Your Status\n\n"
            f"🤖 Current Assistant: {active_agent.title()}\n\n"
            f"📋 Subscription: {subscription['tier'].title()}\n"
            f"📈 Usage Today: {usage['current_usage']}/{usage['daily_limit']}\n"
            f"⏰ Resets: {usage.get('reset_time', 'Unknown')}\n\n"
            f"✅ Available Assistants:\n"
        )

        for graph in subscription.get("allowed_graphs", []):
            status_text += f"  • {graph.title()}\n"

        await query.edit_message_text(status_text)

    except Exception as e:
        logger.error("Failed to get status", exc_info=True)

        # Check if it's a 404 (endpoint not implemented)
        error_msg = str(e)
        if "404" in error_msg:
            await query.edit_message_text(
                "📊 Status Information\n\n"
                "🤖 Current Assistant: "
                + (await state.get_active_agent(chat_id)).title()
                + "\n\n"
                "ℹ️ The subscription system is being set up.\n"
                "For now, you have access to the ToDo Assistant!\n\n"
                "Full status tracking coming soon! 🚀"
            )
        else:
            await query.edit_message_text(
                "Sorry, I couldn't retrieve your status. Please try again later."
            )
