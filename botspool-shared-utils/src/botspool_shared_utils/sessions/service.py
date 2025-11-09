"""High-level session service with Postgres persistence and Redis cache."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from botspool_shared_utils.database import DatabaseManager
from botspool_shared_utils.database.models import SessionRecordModel
from botspool_shared_utils.models.enums import FrontendType
from botspool_shared_utils.redis_utils import RedisManager

from .cache import SessionCache
from .config import SessionSettings
from .repository import SessionRepository
from ..models.session import SessionCreate, SessionRecord, SessionUpdate

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.utcnow()


def _normalize_dt(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def _normalize_session(record: SessionRecord) -> SessionRecord:
    return record.model_copy(
        update={
            "expires_at": _normalize_dt(record.expires_at),
            "last_activity_at": _normalize_dt(record.last_activity_at) or _now(),
            "created_at": _normalize_dt(record.created_at) or _now(),
            "updated_at": _normalize_dt(record.updated_at) or _now(),
        }
    )


class SessionService:
    """Facade that exposes durable session operations."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        redis_manager: Optional[RedisManager] = None,
        settings: Optional[SessionSettings] = None,
    ) -> None:
        self._settings = settings or SessionSettings.from_env()
        self._repository = SessionRepository(db_manager)
        self._cache: Optional[SessionCache] = None

        if (
            redis_manager
            and redis_manager.redis_client
            and self._settings.cache_enabled
        ):
            self._cache = SessionCache(redis_manager.redis_client, self._settings)

    async def start_session(self, payload: SessionCreate) -> SessionRecord:
        """Create or refresh a session for a frontend/chat combination."""

        frontend_type = FrontendType(payload.frontend_type)
        expires_at = payload.expires_at or (
            _now() + timedelta(seconds=self._settings.default_ttl_seconds)
        )
        now_ts = _now()

        existing = await self._repository.get_by_frontend_reference(
            frontend_type, payload.chat_id
        )

        write_payload: Dict[str, Any] = {
            "frontend_type": frontend_type,
            "chat_id": payload.chat_id,
            "user_id": payload.user_id,
            "current_agent": payload.current_agent,
            "locale": payload.locale,
            "state_blob": payload.state_payload,
            "expires_at": expires_at,
            "last_activity_at": now_ts,
        }

        if existing:
            updated = {
                k: v
                for k, v in write_payload.items()
                if v is not None
                or k in {"state_blob", "expires_at", "last_activity_at"}
            }
            record = await self._repository.update(existing.id, updated) or existing
        else:
            record = await self._repository.create(write_payload)

        session = _normalize_session(self._to_model(record))
        await self._cache_write(session)
        return session

    async def get_session(
        self, frontend_type: FrontendType, chat_id: str
    ) -> Optional[SessionRecord]:
        """Fetch session state, preferring the cache when available."""

        frontend = FrontendType(frontend_type)

        cached = await self._cache_read(frontend, chat_id)
        if cached:
            return cached

        record = await self._repository.get_by_frontend_reference(frontend, chat_id)
        if not record:
            return None

        session = _normalize_session(self._to_model(record))
        await self._cache_write(session)
        return session

    async def update_session(
        self,
        frontend_type: FrontendType,
        chat_id: str,
        updates: SessionUpdate,
    ) -> Optional[SessionRecord]:
        frontend = FrontendType(frontend_type)
        record = await self._repository.get_by_frontend_reference(frontend, chat_id)
        if not record:
            return None

        update_dict: Dict[str, Any] = {}
        if updates.user_id is not None:
            update_dict["user_id"] = updates.user_id
        if updates.current_agent is not None:
            update_dict["current_agent"] = updates.current_agent
        if updates.locale is not None:
            update_dict["locale"] = updates.locale
        if updates.state_payload is not None:
            update_dict["state_blob"] = updates.state_payload
        if updates.expires_at is not None:
            update_dict["expires_at"] = _normalize_dt(updates.expires_at)

        update_dict["last_activity_at"] = (
            _normalize_dt(updates.last_activity_at) or _now()
        )

        updated = await self._repository.update(record.id, update_dict)
        if not updated:
            return None

        session = _normalize_session(self._to_model(updated))
        await self._cache_write(session)
        return session

    async def clear_session(self, frontend_type: FrontendType, chat_id: str) -> bool:
        frontend = FrontendType(frontend_type)
        record = await self._repository.get_by_frontend_reference(frontend, chat_id)
        if not record:
            return False

        removed = await self._repository.delete(record.id)
        if removed:
            await self._cache_delete(frontend, chat_id)
        return removed

    async def list_sessions_for_user(
        self, user_id: UUID, limit: int = 50
    ) -> List[SessionRecord]:
        records = await self._repository.list_by_user(user_id, limit)
        return [self._to_model(record) for record in records]

    async def purge_expired(self) -> int:
        count = await self._repository.purge_expired(_now())
        return count

    async def _cache_write(self, session: SessionRecord) -> None:
        if not self._cache:
            return

        normalized = _normalize_session(session)

        ttl_seconds: Optional[int] = None
        if normalized.expires_at:
            ttl_seconds = max(0, int((normalized.expires_at - _now()).total_seconds()))
            if ttl_seconds == 0:
                await self._cache_delete(normalized.frontend_type, normalized.chat_id)
                return

        payload = normalized.model_dump(mode="python", by_alias=False)
        await self._cache.set(
            normalized.frontend_type,
            normalized.chat_id,
            payload,
            ttl_seconds=ttl_seconds,
        )

    async def _cache_read(
        self, frontend_type: FrontendType, chat_id: str
    ) -> Optional[SessionRecord]:
        if not self._cache:
            return None
        payload = await self._cache.get(frontend_type, chat_id)
        if not payload:
            return None
        try:
            return _normalize_session(SessionRecord(**payload))
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed to deserialize cached session for %s/%s: %s",
                frontend_type,
                chat_id,
                exc,
            )
            await self._cache_delete(frontend_type, chat_id)
            return None

    async def _cache_delete(self, frontend_type: FrontendType, chat_id: str) -> None:
        if not self._cache:
            return
        await self._cache.delete(frontend_type, chat_id)

    @staticmethod
    def _to_model(record: SessionRecordModel) -> SessionRecord:
        return SessionRecord(
            id=record.id,
            frontend_type=record.frontend_type,
            chat_id=record.chat_id,
            user_id=record.user_id,
            current_agent=record.current_agent,
            locale=record.locale,
            state_payload=record.state_blob or {},
            expires_at=_normalize_dt(record.expires_at),
            last_activity_at=_normalize_dt(record.last_activity_at),
            created_at=_normalize_dt(record.created_at) or _now(),
            updated_at=_normalize_dt(record.updated_at) or _now(),
        )
