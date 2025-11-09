"""Configuration helpers for session management."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class SessionSettings:
    """Runtime configuration for the session service."""

    default_ttl_seconds: int = 86400
    cache_enabled: bool = True
    cache_ttl_seconds: int = 900
    redis_namespace: str = "session-record"
    prune_batch_size: int = 200

    @classmethod
    def from_env(cls) -> "SessionSettings":
        """Construct settings from environment variables."""
        return cls(
            default_ttl_seconds=_env_int("SESSION_DEFAULT_TTL_SECONDS", 86400),
            cache_enabled=_env_bool("SESSION_CACHE_ENABLED", True),
            cache_ttl_seconds=_env_int("SESSION_CACHE_TTL_SECONDS", 900),
            redis_namespace=os.getenv("SESSION_CACHE_NAMESPACE", "session-record"),
            prune_batch_size=_env_int("SESSION_PRUNE_BATCH_SIZE", 200),
        )

    def cache_key(self, frontend_type: str, chat_id: str) -> str:
        """Build a cache key for the provided frontend/chat combination."""
        return f"{self.redis_namespace}:{frontend_type}:{chat_id}"
