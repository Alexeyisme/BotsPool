"""Redis cache helpers for session records."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as redis

from botspool_shared_utils.models.enums import FrontendType

from .config import SessionSettings

logger = logging.getLogger(__name__)


class SessionCache:
    """Thin wrapper around Redis for storing session records."""

    def __init__(self, redis_client: redis.Redis, settings: SessionSettings):
        self._redis = redis_client
        self._settings = settings

    def _key(self, frontend_type: str, chat_id: str) -> str:
        frontend_value = (
            frontend_type.value
            if isinstance(frontend_type, FrontendType)
            else str(frontend_type)
        )
        return self._settings.cache_key(frontend_value, chat_id)

    async def get(self, frontend_type: str, chat_id: str) -> Optional[Dict[str, Any]]:
        key = self._key(frontend_type, chat_id)
        payload = await self._redis.get(key)
        if payload is None:
            return None
        try:
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            logger.warning(
                "Failed to decode session cache payload for %s: %s", key, exc
            )
            await self._redis.delete(key)
            return None

    async def set(
        self,
        frontend_type: str,
        chat_id: str,
        payload: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        key = self._key(frontend_type, chat_id)
        ttl = ttl_seconds or self._settings.cache_ttl_seconds
        await self._redis.setex(key, ttl, json.dumps(payload, default=str))

    async def delete(self, frontend_type: str, chat_id: str) -> None:
        key = self._key(frontend_type, chat_id)
        await self._redis.delete(key)
