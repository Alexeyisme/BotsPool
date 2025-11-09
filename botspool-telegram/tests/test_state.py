"""Unit tests for Redis state management"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

import pytest
import fakeredis.aioredis
from cryptography.fernet import Fernet

from botspool_shared_utils.models import (
    FrontendType,
    SessionCreate,
    SessionRecord,
    SessionUpdate,
)

from src.bot.state import SessionState


class FakeSessionService:
    """Lightweight in-memory session store used for unit testing."""

    def __init__(self):
        self._sessions: Dict[str, SessionRecord] = {}

    async def get_session(
        self, frontend_type: FrontendType, chat_id: str
    ) -> Optional[SessionRecord]:
        return self._sessions.get(self._key(frontend_type, chat_id))

    async def start_session(self, payload: SessionCreate) -> SessionRecord:
        record = SessionRecord(
            id=uuid4(),
            frontend_type=payload.frontend_type,
            chat_id=payload.chat_id,
            user_id=payload.user_id,
            current_agent=payload.current_agent,
            locale=payload.locale,
            state_payload=payload.state_payload,
            expires_at=payload.expires_at,
            last_activity_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self._sessions[self._key(payload.frontend_type, payload.chat_id)] = record
        return record

    async def update_session(
        self,
        frontend_type: FrontendType,
        chat_id: str,
        updates: SessionUpdate,
    ) -> Optional[SessionRecord]:
        key = self._key(frontend_type, chat_id)
        record = self._sessions.get(key)
        if not record:
            return None

        record_dict = record.model_dump()
        if updates.user_id is not None:
            record_dict["user_id"] = updates.user_id
        if updates.current_agent is not None:
            record_dict["current_agent"] = updates.current_agent
        if updates.locale is not None:
            record_dict["locale"] = updates.locale
        if updates.state_payload is not None:
            record_dict["state_payload"] = updates.state_payload
        if updates.expires_at is not None:
            record_dict["expires_at"] = updates.expires_at

        record_dict["last_activity_at"] = datetime.utcnow()
        record_dict["updated_at"] = datetime.utcnow()
        record = SessionRecord(**record_dict)
        self._sessions[key] = record
        return record

    async def clear_session(self, frontend_type: FrontendType, chat_id: str) -> bool:
        return self._sessions.pop(self._key(frontend_type, chat_id), None) is not None

    def _key(self, frontend_type: FrontendType, chat_id: str) -> str:
        return f"{frontend_type}:{chat_id}"


@pytest.fixture
async def redis_client():
    """Fixture for fake Redis client"""
    client = fakeredis.aioredis.FakeRedis(decode_responses=False)
    yield client
    await client.close()


@pytest.fixture
def encryption_key() -> str:
    return Fernet.generate_key().decode()


@pytest.fixture
def fake_session_service():
    return FakeSessionService()


@pytest.fixture
def state_manager(redis_client, encryption_key, fake_session_service):
    """Fixture for SessionState"""
    return SessionState(
        redis_client, encryption_key, fake_session_service, default_agent="todo"
    )


@pytest.mark.asyncio
async def test_set_get_active_agent(state_manager):
    """Test setting and getting active agent"""
    chat_id = 12345
    agent = "email"

    await state_manager.set_active_agent(chat_id, agent)
    result = await state_manager.get_active_agent(chat_id)

    assert result == agent


@pytest.mark.asyncio
async def test_get_active_agent_default(state_manager):
    """Test getting active agent returns default 'todo'"""
    chat_id = 99999
    result = await state_manager.get_active_agent(chat_id)

    assert result == "todo"


@pytest.mark.asyncio
async def test_store_get_tokens(state_manager):
    """Test storing and retrieving tokens"""
    chat_id = 12345
    access_token = "test_access_token"
    refresh_token = "test_refresh_token"
    expires_in = 3600

    await state_manager.store_tokens(chat_id, access_token, refresh_token, expires_in)

    retrieved_access = await state_manager.get_token(chat_id)
    retrieved_refresh = await state_manager.get_refresh_token(chat_id)

    assert retrieved_access == access_token
    assert retrieved_refresh == refresh_token


@pytest.mark.asyncio
async def test_clear_session(state_manager):
    """Test clearing session removes all data"""
    chat_id = 12345

    # Set some data
    await state_manager.set_active_agent(chat_id, "email")
    await state_manager.store_tokens(chat_id, "token1", "token2", 3600)

    # Clear session
    await state_manager.clear_session(chat_id)

    # Verify data is cleared
    token = await state_manager.get_token(chat_id)
    assert token is None

    # Active agent should return default
    agent = await state_manager.get_active_agent(chat_id)
    assert agent == "todo"
