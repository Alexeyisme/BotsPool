"""Integration tests for the ToDoMemory persistence layer."""

import pytest
from uuid import uuid4

from botspool_shared_utils.database import create_connection_pool, close_connection_pool
from botspool_shared_utils.database.models import Base

from ..config import Settings
from ..memory.todo_memory import ToDoMemory


@pytest.mark.asyncio
async def test_memory_crud_cycle(tmp_path):
    db_path = tmp_path / "todo_memory.db"
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{db_path}",
        redis_url="redis://localhost:6379/15",
    )

    manager = await create_connection_pool(settings.database_url)
    async with manager.engine.begin() as conn:  # type: ignore[union-attr]
        await conn.run_sync(Base.metadata.create_all)

    memory = ToDoMemory(settings)

    user_id = str(uuid4())

    # Profile
    profile_id = await memory.save_profile(user_id, {"name": "Tester"})
    assert profile_id
    profile = await memory.get_profile(user_id)
    assert profile == {"name": "Tester"}

    # ToDo CRUD
    todo_id = await memory.save_todo(
        user_id,
        {
            "task": "Document persistence",
            "status": "not_started",
            "solutions": ["Write tests"],
        },
    )
    assert todo_id

    todos = await memory.get_todos(user_id)
    assert len(todos) == 1
    assert todos[0]["task"] == "Document persistence"

    updated = await memory.update_todo(todo_id, {"status": "in_progress"})
    assert updated is True

    todos = await memory.get_todos(user_id, status="in_progress")
    assert len(todos) == 1

    deleted = await memory.delete_todo(todo_id)
    assert deleted is True

    # Instructions
    instructions_id = await memory.save_instructions(user_id, "Keep tasks small")
    assert instructions_id
    instructions = await memory.get_instructions(user_id)
    assert instructions == "Keep tasks small"

    stats = await memory.get_memory_stats(user_id)
    assert stats["todo_count"] == 0
    assert stats["has_instructions"] is True

    await close_connection_pool()


@pytest.mark.asyncio
async def test_memory_stats_without_db():
    memory = ToDoMemory(Settings())
    await close_connection_pool()
    stats = await memory.get_memory_stats(str(uuid4()))
    assert stats["storage_mode"] == "in_memory_only"
