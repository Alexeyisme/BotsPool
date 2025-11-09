"""Integration tests for ToDo-related database queries."""

import pytest
from uuid import uuid4

from botspool_shared_utils.database.queries import ToDoQueries


@pytest.mark.asyncio
async def test_upsert_profile(test_database_session):
    queries = ToDoQueries(test_database_session)
    user_id = uuid4()
    profile = {"name": "Alice", "timezone": "UTC"}

    record = await queries.upsert_profile(user_id, profile)
    assert record.profile == profile

    # Update path
    updated = {"name": "Alice", "timezone": "Europe/Berlin"}
    record = await queries.upsert_profile(user_id, updated)
    assert record.profile == updated


@pytest.mark.asyncio
async def test_todo_crud_cycle(test_database_session):
    queries = ToDoQueries(test_database_session)
    user_id = uuid4()

    todo = await queries.create_todo(
        user_id,
        {
            "task": "Write integration tests",
            "status": "not_started",
            "solutions": ["Draft outline"],
        },
    )

    todos = await queries.list_todos(user_id)
    assert len(todos) == 1
    assert todos[0].task == "Write integration tests"

    await queries.update_todo(todo.id, {"status": "in_progress"})
    todos = await queries.list_todos(user_id)
    assert todos[0].status == "in_progress"

    deleted = await queries.delete_todo(todo.id)
    assert deleted is True

    todos = await queries.list_todos(user_id)
    assert len(todos) == 0


@pytest.mark.asyncio
async def test_upsert_instructions(test_database_session):
    queries = ToDoQueries(test_database_session)
    user_id = uuid4()

    record = await queries.upsert_instructions(user_id, "Keep updates concise")
    assert record.instructions == "Keep updates concise"

    record = await queries.upsert_instructions(user_id, "Include timestamps")
    assert record.instructions == "Include timestamps"
