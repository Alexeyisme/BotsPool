"""Database repository for session records."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from botspool_shared_utils.database import DatabaseManager
from botspool_shared_utils.database.models import SessionRecordModel
from botspool_shared_utils.database.queries import SessionQueries
from botspool_shared_utils.models.enums import FrontendType


class SessionRepository:
    """Abstraction over SQLAlchemy queries for session records."""

    def __init__(self, db_manager: DatabaseManager):
        self._db_manager = db_manager

    async def get_by_id(self, record_id: UUID) -> Optional[SessionRecordModel]:
        async with self._db_manager.get_session_context() as session:
            queries = SessionQueries(session)
            return await queries.get_by_id(record_id)

    async def get_by_frontend_reference(
        self,
        frontend_type: FrontendType,
        chat_id: str,
    ) -> Optional[SessionRecordModel]:
        async with self._db_manager.get_session_context() as session:
            queries = SessionQueries(session)
            return await queries.get_by_frontend_reference(frontend_type, chat_id)

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
    ) -> List[SessionRecordModel]:
        async with self._db_manager.get_session_context() as session:
            queries = SessionQueries(session)
            return await queries.list_by_user(user_id, limit)

    async def create(self, payload: Dict[str, Any]) -> SessionRecordModel:
        async with self._db_manager.get_transaction_context() as session:
            queries = SessionQueries(session)
            record = await queries.create_session(payload)
            return record

    async def update(
        self, record_id: UUID, updates: Dict[str, Any]
    ) -> Optional[SessionRecordModel]:
        async with self._db_manager.get_transaction_context() as session:
            queries = SessionQueries(session)
            return await queries.update_session(record_id, updates)

    async def delete(self, record_id: UUID) -> bool:
        async with self._db_manager.get_transaction_context() as session:
            queries = SessionQueries(session)
            return await queries.delete_session(record_id)

    async def purge_expired(self, now_ts: datetime) -> int:
        async with self._db_manager.get_transaction_context() as session:
            queries = SessionQueries(session)
            return await queries.purge_expired(now_ts)
