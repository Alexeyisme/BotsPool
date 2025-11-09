"""Gateway authentication helpers for Telegram users"""
import secrets
import string
import random
import httpx
from typing import Dict


def generate_secure_password(length: int = 24) -> str:
    """
    Generate a secure password that meets Gateway requirements:
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    # Ensure we have at least one of each required character type
    password_chars = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice("!@#$%^&*()-_=+[]{}|;:,.<>?"),
    ]

    # Fill the rest with random characters from all categories
    all_chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    password_chars.extend(random.choice(all_chars) for _ in range(length - 4))

    # Shuffle to avoid predictable patterns
    random.shuffle(password_chars)

    return "".join(password_chars)


async def register_telegram_user(
    telegram_id: int,
    telegram_username: str,
    first_name: str,
    last_name: str,
    gateway_url: str,
    password: str | None = None,
    username_override: str | None = None,
    email_override: str | None = None,
) -> Dict:
    """
    Auto-register Telegram user with synthetic credentials.

    Args:
        telegram_id: Telegram user ID
        telegram_username: Telegram username
        first_name: User's first name
        last_name: User's last name
        gateway_url: Gateway base URL

    Returns:
        Registration response with tokens
    """
    username = username_override or f"telegram_{telegram_id}"
    email = email_override or f"telegram_{telegram_id}@botspool.internal"
    password = password or generate_secure_password(24)
    display_name = f"{first_name} {last_name}".strip() or username

    payload = {
        "username": username,
        "email": email,
        "password": password,
        "display_name": display_name,
        "frontend_type": "telegram",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{gateway_url}/api/v1/auth/register", json=payload
        )
        response.raise_for_status()
        return response.json()


async def login_telegram_user(username: str, password: str, gateway_url: str) -> Dict:
    """Login existing telegram user using stored credentials."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{gateway_url}/api/v1/auth/login",
            json={
                "username": username,
                "password": password,
                "frontend_type": "telegram",
            },
        )
        response.raise_for_status()
        return response.json()


async def refresh_access_token(refresh_token: str, gateway_url: str) -> Dict:
    """
    Refresh access token using refresh token.

    Args:
        refresh_token: Refresh token
        gateway_url: Gateway base URL

    Returns:
        New token response
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{gateway_url}/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        response.raise_for_status()
        return response.json()
