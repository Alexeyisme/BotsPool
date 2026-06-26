"""Gateway API client with token management and error handling"""
import logging
import httpx
from httpx import HTTPStatusError
from typing import Dict, List
from ..models import GraphUnavailableError, AuthRefreshError
from .auth import refresh_access_token


class GatewayClient:
    """Client for interacting with BotsPool Gateway API"""

    def __init__(self, base_url: str, state_manager):
        """
        Initialize Gateway client.

        Args:
            base_url: Gateway base URL
            state_manager: SessionState instance for token management
        """
        self.base_url = base_url
        self.state = state_manager
        self.client = httpx.AsyncClient(timeout=30.0)
        self.logger = logging.getLogger(__name__)

    async def ensure_valid_token(self, chat_id: int) -> str:
        """
        Get valid token, refresh if needed.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Valid access token
        """
        if await self.state.token_needs_refresh(chat_id):
            refresh_token = await self.state.get_refresh_token(chat_id)
            if not refresh_token:
                self.logger.warning(
                    "Refresh token missing for chat %s. Clearing session.", chat_id
                )
                await self.state.clear_session(chat_id, preserve_credentials=True)
                raise AuthRefreshError("Missing refresh token")

            try:
                new_tokens = await refresh_access_token(refresh_token, self.base_url)
            except HTTPStatusError as exc:
                if exc.response.status_code in {401, 403, 422}:
                    self.logger.warning(
                        "Token refresh failed for chat %s with status %s. Clearing session.",
                        chat_id,
                        exc.response.status_code,
                    )
                    await self.state.clear_session(chat_id, preserve_credentials=True)
                    raise AuthRefreshError() from exc
                raise
            await self.state.store_tokens(
                chat_id,
                new_tokens["access_token"],
                new_tokens.get("refresh_token", refresh_token),
                new_tokens["expires_in"],
            )

        return await self.state.get_token(chat_id)

    async def get_available_graphs(self, chat_id: int) -> List[Dict]:
        """
        Get graphs available to user based on subscription.

        Args:
            chat_id: Telegram chat ID

        Returns:
            List of available graphs
        """
        token = await self.ensure_valid_token(chat_id)
        response = await self.client.get(
            f"{self.base_url}/api/v1/graphs",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json().get("graphs", [])

    async def send_message(
        self, chat_id: int, agent: str, message: str, telegram_user_id: int
    ) -> Dict:
        """
        Send message to agent via Gateway.
        Uses compound session_id: {chat_id}_{agent} for per-agent context.

        Args:
            chat_id: Telegram chat ID
            agent: Agent type (todo, email, calendar, etc.)
            message: User message
            telegram_user_id: Telegram user ID

        Returns:
            Agent response

        Raises:
            GraphUnavailableError: If graph service is unavailable
        """
        token = await self.ensure_valid_token(chat_id)
        session_id = f"{chat_id}_{agent}"  # Per-agent session isolation

        # Get BotsPool UUID from Redis (stored during /start)
        user_uuid = await self.state.get_user_id(chat_id)

        if not user_uuid:
            # Fallback: use telegram_user_id (but log warning)
            self.logger.warning(
                f"No UUID for chat {chat_id}, using telegram_id {telegram_user_id}"
            )
            user_uuid = str(telegram_user_id)

        payload = {
            "message": message,
            "user_id": user_uuid,  # Use BotsPool UUID instead of telegram_user_id
            "session_id": session_id,
            "metadata": {
                "frontend": "telegram",
                "chat_id": str(chat_id),
                "telegram_user_id": str(telegram_user_id),
            },
        }

        response = await self.client.post(
            f"{self.base_url}/api/v1/chat/{agent}",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )

        if response.status_code == 503:
            raise GraphUnavailableError(agent)

        response.raise_for_status()
        return response.json()

    async def get_subscription_status(self, chat_id: int) -> Dict:
        """
        Get user subscription and usage information.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Subscription status information
        """
        token = await self.ensure_valid_token(chat_id)
        response = await self.client.get(
            f"{self.base_url}/api/v1/subscription/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
