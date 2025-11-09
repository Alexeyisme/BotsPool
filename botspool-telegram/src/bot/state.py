"""Session state management backed by Redis and the shared session service."""

import time
from typing import Any, Dict, Optional

import redis.asyncio as redis
from cryptography.fernet import Fernet, InvalidToken

from botspool_shared_utils.models import (
    FrontendType,
    SessionCreate,
    SessionRecord,
    SessionUpdate,
)
from botspool_shared_utils.sessions import SessionService


class SessionState:
    """Manage Telegram sessions with durable persistence and cached secrets."""

    def __init__(
        self,
        redis_client: redis.Redis,
        encryption_key: str,
        session_service: SessionService,
        default_agent: str,
    ):
        self.redis = redis_client
        self.session_service = session_service
        self.default_agent = default_agent
        self.frontend = FrontendType.TELEGRAM
        self.SESSION_TTL = 86400  # 24 hours

        if not encryption_key:
            raise ValueError("CREDENTIAL_ENCRYPTION_KEY must be provided")
        try:
            self.cipher = Fernet(
                encryption_key.encode()
                if isinstance(encryption_key, str)
                else encryption_key
            )
        except Exception as exc:  # pragma: no cover - config error
            raise ValueError("Invalid CREDENTIAL_ENCRYPTION_KEY provided") from exc

    async def _ensure_session(self, chat_id: int) -> SessionRecord:
        chat = str(chat_id)
        session = await self.session_service.get_session(self.frontend, chat)
        if session:
            return session

        return await self.session_service.start_session(
            SessionCreate(
                frontend_type=self.frontend,
                chat_id=chat,
                user_id=None,
                current_agent=self.default_agent,
                state_payload={},
            )
        )

    async def _merge_state_payload(self, chat_id: int, updates: Dict[str, Any]) -> None:
        session = await self._ensure_session(chat_id)
        payload = dict(session.state_payload or {})
        payload.update(updates)
        await self.session_service.update_session(
            self.frontend,
            str(chat_id),
            SessionUpdate(state_payload=payload),
        )

    async def set_active_agent(self, chat_id: int, agent: str):
        """Set the active agent and persist it durably."""
        await self._ensure_session(chat_id)
        key = f"telegram:session:{chat_id}:active_agent"
        await self.redis.set(key, agent, ex=self.SESSION_TTL)
        await self.session_service.update_session(
            self.frontend,
            str(chat_id),
            SessionUpdate(current_agent=agent),
        )

    async def get_active_agent(self, chat_id: int) -> str:
        """Get active agent for chat, defaulting to the configured agent."""
        key = f"telegram:session:{chat_id}:active_agent"
        agent = await self.redis.get(key)
        if agent:
            return agent.decode() if isinstance(agent, bytes) else agent

        session = await self.session_service.get_session(self.frontend, str(chat_id))
        if session and session.current_agent:
            await self.redis.set(key, session.current_agent, ex=self.SESSION_TTL)
            return session.current_agent

        await self._ensure_session(chat_id)
        return self.default_agent

    async def store_tokens(
        self, chat_id: int, access_token: str, refresh_token: str, expires_in: int
    ):
        """Store authentication tokens with TTL"""
        await self._ensure_session(chat_id)
        pipe = self.redis.pipeline()
        pipe.set(f"telegram:session:{chat_id}:token", access_token, ex=self.SESSION_TTL)
        pipe.set(
            f"telegram:session:{chat_id}:refresh_token",
            refresh_token,
            ex=self.SESSION_TTL,
        )
        pipe.set(
            f"telegram:session:{chat_id}:token_expires",
            str(time.time() + expires_in),
            ex=self.SESSION_TTL,
        )
        await pipe.execute()

    async def store_password(self, chat_id: int, password: str):
        """Store encrypted password for reuse."""
        key = f"telegram:session:{chat_id}:password"
        token = self.cipher.encrypt(password.encode()).decode()
        await self.redis.set(key, token)

    async def store_username(self, chat_id: int, username: str):
        """Persist username for future logins."""
        key = f"telegram:session:{chat_id}:username"
        await self.redis.set(key, username)

    async def get_password(self, chat_id: int) -> Optional[str]:
        """Retrieve decrypted password if stored."""
        key = f"telegram:session:{chat_id}:password"
        encrypted = await self.redis.get(key)
        if not encrypted:
            return None
        if isinstance(encrypted, bytes):
            encrypted = encrypted.decode()
        try:
            return self.cipher.decrypt(encrypted.encode()).decode()
        except InvalidToken:
            return None

    async def get_username(self, chat_id: int) -> Optional[str]:
        """Retrieve stored username if available."""
        key = f"telegram:session:{chat_id}:username"
        value = await self.redis.get(key)
        if value:
            return value.decode() if isinstance(value, bytes) else value
        return None

    async def get_token(self, chat_id: int) -> Optional[str]:
        """Get access token for chat"""
        key = f"telegram:session:{chat_id}:token"
        token = await self.redis.get(key)
        if token:
            return token.decode() if isinstance(token, bytes) else token
        return None

    async def get_refresh_token(self, chat_id: int) -> Optional[str]:
        """Get refresh token for chat"""
        key = f"telegram:session:{chat_id}:refresh_token"
        token = await self.redis.get(key)
        if token:
            return token.decode() if isinstance(token, bytes) else token
        return None

    async def token_needs_refresh(self, chat_id: int) -> bool:
        """Check if token needs refresh (< 5 minutes remaining)"""
        expires_key = f"telegram:session:{chat_id}:token_expires"
        expires = await self.redis.get(expires_key)
        if not expires:
            return True

        expires_value = expires.decode() if isinstance(expires, bytes) else expires
        return time.time() + 300 > float(expires_value)

    async def set_user_id(self, chat_id: int, user_id: str):
        """Store BotsPool user ID"""
        key = f"telegram:session:{chat_id}:user_id"
        await self.redis.set(key, user_id, ex=self.SESSION_TTL)
        await self._ensure_session(chat_id)
        await self.session_service.update_session(
            self.frontend,
            str(chat_id),
            SessionUpdate(user_id=user_id),
        )

    async def get_user_id(self, chat_id: int) -> Optional[str]:
        """Get BotsPool user UUID"""
        key = f"telegram:session:{chat_id}:user_id"
        user_id = await self.redis.get(key)
        if user_id:
            return user_id.decode() if isinstance(user_id, bytes) else user_id
        session = await self.session_service.get_session(self.frontend, str(chat_id))
        if session and session.user_id:
            await self.redis.set(key, str(session.user_id), ex=self.SESSION_TTL)
            return str(session.user_id)
        return None

    async def set_telegram_user_id(self, chat_id: int, telegram_user_id: int):
        """Store Telegram user ID"""
        key = f"telegram:session:{chat_id}:telegram_user_id"
        await self.redis.set(key, str(telegram_user_id), ex=self.SESSION_TTL)
        await self._merge_state_payload(
            chat_id, {"telegram_user_id": str(telegram_user_id)}
        )

    async def refresh_activity(self, chat_id: int):
        """Update TTL on all session keys to keep session alive"""
        pattern = f"telegram:session:{chat_id}:*"
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            key_str = key.decode() if isinstance(key, bytes) else key
            # Skip credential keys to avoid applying TTL (permanent storage)
            if key_str.endswith(":password") or key_str.endswith(":username"):
                continue
            keys.append(key)

        if keys:
            pipe = self.redis.pipeline()
            for key in keys:
                pipe.expire(key, self.SESSION_TTL)
            await pipe.execute()
        await self._ensure_session(chat_id)
        await self.session_service.update_session(
            self.frontend,
            str(chat_id),
            SessionUpdate(),
        )

    async def clear_session(self, chat_id: int, preserve_credentials: bool = False):
        """Clear session data, optionally keeping stored credentials."""
        pattern = f"telegram:session:{chat_id}:*"
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            key_str = key.decode() if isinstance(key, bytes) else key
            if preserve_credentials and (
                key_str.endswith(":password") or key_str.endswith(":username")
            ):
                continue
            keys.append(key)

        if keys:
            await self.redis.delete(*keys)
        await self.session_service.clear_session(self.frontend, str(chat_id))
