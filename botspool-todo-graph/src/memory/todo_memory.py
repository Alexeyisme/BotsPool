"""PostgreSQL-backed memory helpers for the ToDo graph service."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from botspool_shared_utils.database import ToDoQueries, get_database_manager
from botspool_shared_utils.database.models import ToDoItemModel
from botspool_shared_utils.errors import ConfigurationError

from ..config import Settings

logger = logging.getLogger(__name__)


def _ensure_uuid(value: str) -> UUID:
    """Normalise arbitrary identifiers to UUID objects."""
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _parse_deadline(value: Optional[Any]) -> Optional[datetime]:
    """Best-effort parsing for deadline values."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _serialize_todo(record: ToDoItemModel) -> Dict[str, Any]:
    """Convert ORM instances to simple dictionaries."""
    return {
        "todo_id": str(record.id),
        "user_id": str(record.user_id),
        "task": record.task,
        "status": record.status,
        "priority": record.priority,
        "category": record.category,
        "time_to_complete": record.time_to_complete,
        "deadline": record.deadline.isoformat() if record.deadline else None,
        "solutions": record.solutions or [],
        "extra": record.extra or {},
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


class ToDoMemory:
    """Database-backed persistence for agent memory."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.namespace = settings.memory_namespace

    async def save_profile(self, user_id: str, profile_data: Dict[str, Any]) -> str:
        """Persist or update structured profile information."""
        manager = self._get_db_manager()
        async with manager.get_transaction_context() as session:
            queries = ToDoQueries(session)
            record = await queries.upsert_profile(_ensure_uuid(user_id), profile_data)
            return str(record.id)

    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        manager = self._get_db_manager()
        async with manager.get_session_context() as session:
            queries = ToDoQueries(session)
            record = await queries.get_profile(_ensure_uuid(user_id))
            return record.profile if record else None

    async def save_todo(self, user_id: str, todo_data: Dict[str, Any]) -> str:
        payload = {
            "task": todo_data["task"],
            "status": todo_data.get("status", "not_started"),
            "priority": todo_data.get("priority"),
            "category": todo_data.get("category"),
            "time_to_complete": todo_data.get("time_to_complete"),
            "deadline": _parse_deadline(todo_data.get("deadline")),
            "solutions": todo_data.get("solutions") or [],
            "extra": todo_data.get("extra"),
        }

        manager = self._get_db_manager()
        async with manager.get_transaction_context() as session:
            queries = ToDoQueries(session)
            record = await queries.create_todo(_ensure_uuid(user_id), payload)
            return str(record.id)

    async def get_todos(
        self, user_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        manager = self._get_db_manager()
        async with manager.get_session_context() as session:
            queries = ToDoQueries(session)
            records = await queries.list_todos(_ensure_uuid(user_id), status)
            return [_serialize_todo(record) for record in records]

    async def update_todo(self, todo_id: str, updates: Dict[str, Any]) -> bool:
        manager = self._get_db_manager()
        async with manager.get_transaction_context() as session:
            queries = ToDoQueries(session)
            prepared = self._prepare_updates(updates)
            record = await queries.update_todo(_ensure_uuid(todo_id), prepared)
            return record is not None

    async def delete_todo(self, todo_id: str) -> bool:
        manager = self._get_db_manager()
        async with manager.get_transaction_context() as session:
            queries = ToDoQueries(session)
            return await queries.delete_todo(_ensure_uuid(todo_id))

    async def save_instructions(self, user_id: str, instructions: str) -> str:
        manager = self._get_db_manager()
        async with manager.get_transaction_context() as session:
            queries = ToDoQueries(session)
            record = await queries.upsert_instructions(
                _ensure_uuid(user_id), instructions
            )
            return str(record.id)

    async def get_instructions(self, user_id: str) -> Optional[str]:
        manager = self._get_db_manager()
        async with manager.get_session_context() as session:
            queries = ToDoQueries(session)
            record = await queries.get_instructions(_ensure_uuid(user_id))
            return record.instructions if record else None

    async def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        try:
            manager = self._get_db_manager()
            async with manager.get_session_context() as session:
                queries = ToDoQueries(session)
                uuid = _ensure_uuid(user_id)
                profile = await queries.get_profile(uuid)
                todos = await queries.list_todos(uuid)
                instructions = await queries.get_instructions(uuid)

            return {
                "user_id": user_id,
                "has_profile": profile is not None,
                "todo_count": len(todos),
                "has_instructions": instructions is not None,
                "last_updated": datetime.utcnow().isoformat(),
            }
        except ConfigurationError as exc:
            logger.warning("Database manager is not initialised: %s", exc)
        except Exception as exc:  # pragma: no cover - fallback path
            logger.warning("Memory stats unavailable due to error: %s", exc)

        return {
            "user_id": user_id,
            "has_profile": False,
            "todo_count": 0,
            "has_instructions": False,
            "last_updated": datetime.utcnow().isoformat(),
            "storage_mode": "in_memory_only",
        }

    def _prepare_updates(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        prepared: Dict[str, Any] = {}

        for field in {"task", "status", "priority", "category"}:
            if field in updates:
                prepared[field] = updates[field]

        if "time_to_complete" in updates:
            prepared["time_to_complete"] = updates["time_to_complete"]

        if "deadline" in updates:
            prepared["deadline"] = _parse_deadline(updates["deadline"])

        if "solutions" in updates:
            prepared["solutions"] = updates.get("solutions") or []

        if "extra" in updates:
            prepared["extra"] = updates.get("extra")

        return prepared

    def _get_db_manager(self):
        try:
            return get_database_manager()
        except ConfigurationError as exc:  # pragma: no cover - configuration error path
            raise RuntimeError("Database manager not initialised") from exc
