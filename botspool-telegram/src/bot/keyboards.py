"""Inline keyboard builders for Telegram bot"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict


async def build_main_menu_keyboard(
    gateway_client, chat_id: int
) -> InlineKeyboardMarkup:
    """
    Build main menu with subscription-aware agent buttons.

    Args:
        gateway_client: GatewayClient instance
        chat_id: Telegram chat ID

    Returns:
        InlineKeyboardMarkup with available agents
    """
    # Get available graphs from user's subscription
    try:
        available_graphs = await gateway_client.get_available_graphs(chat_id)
    except Exception:
        # Fallback to default if can't fetch
        available_graphs = [{"type": "todo", "status": "available"}]

    # Map graph types to emoji and display names
    graph_display = {
        "todo": ("📝", "ToDo Assistant"),
        "email": ("📧", "Email Assistant"),
        "calendar": ("📅", "Calendar Assistant"),
        "document": ("📄", "Document Assistant"),
        "code": ("💻", "Code Assistant"),
        "research": ("🔍", "Research Assistant"),
    }

    # Build keyboard with available graphs
    keyboard = []
    row = []
    for graph in available_graphs:
        graph_type = graph["type"]
        if graph_type in graph_display and graph.get("status") == "available":
            emoji, name = graph_display[graph_type]
            button = InlineKeyboardButton(
                f"{emoji} {name}", callback_data=f"select_graph:{graph_type}"
            )
            row.append(button)
            if len(row) == 2:
                keyboard.append(row)
                row = []

    # Add remaining buttons
    if row:
        keyboard.append(row)

    # Add utility buttons
    keyboard.append(
        [
            InlineKeyboardButton("ℹ️ Status", callback_data="show_status"),
            InlineKeyboardButton("❓ Help", callback_data="show_help"),
        ]
    )

    return InlineKeyboardMarkup(keyboard)


def build_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Build confirmation keyboard.

    Returns:
        InlineKeyboardMarkup with confirm/cancel buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Cancel", callback_data="confirm_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
