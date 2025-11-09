"""Handler for /start command"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from httpx import HTTPStatusError
from ..keyboards import build_main_menu_keyboard

logger = logging.getLogger(__name__)


async def start_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state,
    gateway_client,
    gateway_auth,
    gateway_url: str,
):
    """
    Handle /start command.
    - Check if private chat only
    - Auto-register new users with Telegram auth
    - Store tokens in Redis
    - Show welcome message with main menu
    """
    # Only allow private chats
    if update.effective_chat.type != "private":
        await update.message.reply_text(
            "This bot only works in private chats. Please message me directly!"
        )
        return

    chat_id = update.effective_chat.id
    telegram_user = update.effective_user

    logger.info(
        "User started bot",
        extra={
            "telegram_user_id": telegram_user.id,
            "telegram_username": telegram_user.username,
            "chat_id": chat_id,
        },
    )

    # Check if user already registered
    existing_token = await state.get_token(chat_id)
    stored_password = await state.get_password(chat_id)
    stored_username = await state.get_username(chat_id)

    if not existing_token:
        auth_response = None
        is_new_user = False

        # Try to reuse stored credentials first
        if stored_username and stored_password:
            logger.info(
                "Attempting login with stored credentials",
                extra={
                    "telegram_user_id": telegram_user.id,
                    "username": stored_username,
                },
            )
            try:
                auth_response = await gateway_auth.login_telegram_user(
                    username=stored_username,
                    password=stored_password,
                    gateway_url=gateway_url,
                )
                is_new_user = False
            except HTTPStatusError as login_error:
                logger.warning(
                    "Stored credentials rejected, falling back to registration",
                    extra={
                        "telegram_user_id": telegram_user.id,
                        "status_code": login_error.response.status_code
                        if login_error.response
                        else None,
                    },
                )
                auth_response = None

        if auth_response is None:
            # Auto-register new user or create temporary account
            try:
                registration_password = gateway_auth.generate_secure_password()
                username = f"telegram_{telegram_user.id}"
                auth_response = await gateway_auth.register_telegram_user(
                    telegram_id=telegram_user.id,
                    telegram_username=telegram_user.username or "",
                    first_name=telegram_user.first_name or "",
                    last_name=telegram_user.last_name or "",
                    gateway_url=gateway_url,
                    password=registration_password,
                    username_override=username,
                )
                await state.store_password(chat_id, registration_password)
                await state.store_username(chat_id, username)
                is_new_user = True
            except HTTPStatusError as e:
                status = e.response.status_code if e.response else None
                if status in (400, 409):
                    logger.info(
                        "User already registered but credentials unavailable; creating temporary session",
                        extra={"telegram_user_id": telegram_user.id},
                    )
                    auth_response, is_new_user = await _create_temporary_session(
                        update, gateway_url, gateway_auth, state, telegram_user, chat_id
                    )
                    if auth_response is None:
                        return
                else:
                    logger.error(
                        "Failed to register user",
                        exc_info=True,
                        extra={"status_code": status},
                    )
                    await update.message.reply_text(
                        "Sorry, I couldn't register you. Please try again later or contact support."
                    )
                    return
            except Exception as exc:
                logger.error("Unexpected error during registration", exc_info=True)
                await update.message.reply_text(
                    "Sorry, I couldn't register you. Please try again later or contact support."
                )
                return

        # Store tokens
        await state.store_tokens(
            chat_id,
            auth_response["access_token"],
            auth_response.get("refresh_token", ""),
            auth_response["expires_in"],
        )

        # Store user info
        await state.set_user_id(chat_id, auth_response["user"]["id"])
        await state.set_telegram_user_id(chat_id, telegram_user.id)
        # Ensure credentials are persisted/re-freshed
        user_username = (
            auth_response["user"].get("username") if auth_response.get("user") else None
        )
        if user_username:
            await state.store_username(chat_id, user_username)
        elif stored_username:
            await state.store_username(chat_id, stored_username)
        if stored_password:
            await state.store_password(chat_id, stored_password)

        # Set default agent
        await state.set_active_agent(chat_id, "todo")

        if is_new_user:
            welcome_text = (
                f"Welcome to BotsPool, {telegram_user.first_name}! 🎉\n\n"
                "I'm your unified AI assistant platform. "
                "I can help you with tasks, emails, calendar, and more!\n\n"
                "Select an assistant below to get started:"
            )
        else:
            welcome_text = (
                f"Session restored, {telegram_user.first_name}! 👋\n\n"
                "Select an assistant to continue:"
            )
    else:
        welcome_text = (
            f"Welcome back, {telegram_user.first_name}! 👋\n\n"
            "Select an assistant to continue:"
        )

    # Show main menu
    keyboard = await build_main_menu_keyboard(gateway_client, chat_id)
    await update.message.reply_text(welcome_text, reply_markup=keyboard)


# Helper function
async def _create_temporary_session(
    update, gateway_url, gateway_auth, state, telegram_user, chat_id
):
    """Create a temporary session with unique credentials."""
    import uuid

    await update.message.reply_text(
        "You're already registered! Your session was cleared.\n\n"
        "Unfortunately, I can't retrieve your session automatically. "
        "Let's create a temporary session so you can keep using the bot."
    )
    unique_suffix = uuid.uuid4().hex[:8]
    temp_username = f"telegram_{telegram_user.id}_temp_{unique_suffix}"
    temp_email = (
        f"telegram_{telegram_user.id}_{chat_id}_{unique_suffix}@botspool.internal"
    )
    temp_password = gateway_auth.generate_secure_password()
    try:
        auth_response = await gateway_auth.register_telegram_user(
            telegram_id=telegram_user.id,
            telegram_username=telegram_user.username or "",
            first_name=telegram_user.first_name or "",
            last_name=telegram_user.last_name or "",
            gateway_url=gateway_url,
            username_override=temp_username,
            email_override=temp_email,
            password=temp_password,
        )
        await state.store_password(chat_id, temp_password)
        await state.store_username(chat_id, temp_username)
        return auth_response, False
    except HTTPStatusError as temp_error:
        logger.error(
            "Failed to create temporary session",
            exc_info=True,
            extra={
                "telegram_user_id": telegram_user.id,
                "status_code": temp_error.response.status_code
                if temp_error.response
                else None,
                "response": temp_error.response.text if temp_error.response else None,
            },
        )
        await update.message.reply_text(
            "Sorry, I couldn't restore your session. Please contact support."
        )
        return None, False
