"""
Unit tests for ToDo Service
"""

import pytest
from unittest.mock import Mock, AsyncMock
from ..services.todo_service import ToDoService
from ..config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return Settings(
        app_name="Test ToDo Graph",
        app_version="1.0.0",
        environment="test",
        debug=True,
        openai_api_key="test_key",
        openai_model="gpt-4o",
    )


@pytest.fixture
def todo_service(mock_settings):
    """ToDo service instance for testing."""
    return ToDoService(mock_settings)


@pytest.mark.asyncio
async def test_process_message_success(todo_service):
    """Test successful message processing."""
    # Mock the agent
    todo_service.agent.process_message = AsyncMock(return_value="Test response")
    todo_service.memory.get_memory_stats = AsyncMock(return_value={"todo_count": 5})

    result = await todo_service.process_message(
        message="Add a task to follow up with client",
        user_id="test_user",
        session_id="test_session",
    )

    assert result["response"] == "Test response"
    assert result["user_id"] == "test_user"
    assert result["session_id"] == "test_session"
    assert "timestamp" in result
    assert "graph_type" in result


@pytest.mark.asyncio
async def test_process_message_validation_error(todo_service):
    """Test message validation error."""
    with pytest.raises(Exception):
        await todo_service.process_message(
            message="", user_id="test_user"  # Empty message should fail validation
        )


@pytest.mark.asyncio
async def test_get_todos(todo_service):
    """Test getting todos."""
    todo_service.memory.get_todos = AsyncMock(
        return_value=[{"task": "Test task", "status": "not_started"}]
    )

    todos = await todo_service.get_todos("test_user")

    assert len(todos) == 1
    assert todos[0]["task"] == "Test task"


@pytest.mark.asyncio
async def test_create_todo(todo_service):
    """Test creating a todo."""
    todo_service.memory.save_todo = AsyncMock(return_value="todo_123")

    result = await todo_service.create_todo(
        "test_user", {"task": "Test task", "status": "not_started"}
    )

    assert result["todo_id"] == "todo_123"
    assert result["user_id"] == "test_user"
    assert result["task"] == "Test task"


@pytest.mark.asyncio
async def test_get_service_stats(todo_service):
    """Test getting service statistics."""
    stats = await todo_service.get_service_stats()

    assert stats["service_name"] == "BotsPool ToDo Graph"
    assert stats["version"] == "1.0.0"
    assert stats["graph_type"] == "todo"
