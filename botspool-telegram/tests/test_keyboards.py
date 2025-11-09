"""Unit tests for keyboard builders"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.bot.keyboards import build_main_menu_keyboard, build_confirmation_keyboard


@pytest.mark.asyncio
async def test_build_main_menu_keyboard():
    """Test building main menu keyboard with available graphs"""
    # Mock gateway client
    gateway_client = AsyncMock()
    gateway_client.get_available_graphs.return_value = [
        {"type": "todo", "status": "available"},
        {"type": "email", "status": "available"},
    ]

    chat_id = 12345
    keyboard = await build_main_menu_keyboard(gateway_client, chat_id)

    # Verify keyboard structure
    assert keyboard is not None
    assert (
        len(keyboard.inline_keyboard) >= 2
    )  # At least graph buttons + utility buttons

    # Verify gateway client was called
    gateway_client.get_available_graphs.assert_called_once_with(chat_id)


@pytest.mark.asyncio
async def test_build_main_menu_keyboard_handles_error():
    """Test building main menu keyboard handles errors gracefully"""
    # Mock gateway client that raises exception
    gateway_client = AsyncMock()
    gateway_client.get_available_graphs.side_effect = Exception("API Error")

    chat_id = 12345
    keyboard = await build_main_menu_keyboard(gateway_client, chat_id)

    # Should still return a keyboard (fallback)
    assert keyboard is not None


def test_build_confirmation_keyboard():
    """Test building confirmation keyboard"""
    keyboard = build_confirmation_keyboard()

    # Verify structure
    assert keyboard is not None
    assert len(keyboard.inline_keyboard) == 1
    assert len(keyboard.inline_keyboard[0]) == 2  # Confirm and Cancel buttons
