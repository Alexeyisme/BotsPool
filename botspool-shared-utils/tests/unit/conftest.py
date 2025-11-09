"""
Unit test configuration and fixtures for botspool-shared-utils
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, Optional
import tempfile
import os

# Test database configuration
TEST_DATABASE_URL = "sqlite:///test.db"
TEST_REDIS_URL = "redis://localhost:6379/15"  # Use test database


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.setex.return_value = True
    mock.delete.return_value = 1
    mock.sadd.return_value = 1
    mock.srem.return_value = 1
    mock.smembers.return_value = set()
    mock.hgetall.return_value = {}
    mock.hset.return_value = 1
    mock.expire.return_value = True
    mock.expireat.return_value = True
    mock.ttl.return_value = 3600
    mock.incr.return_value = 1
    return mock


@pytest.fixture
def mock_database():
    """Mock database connection for testing."""
    mock = AsyncMock()
    mock.execute.return_value = None
    mock.scalar.return_value = None
    mock.scalars.return_value = []
    mock.commit.return_value = None
    mock.rollback.return_value = None
    return mock


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": "user-123",
        "email": "test@example.com",
        "username": "testuser",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8KzKz2O",
        "first_name": "Test",
        "last_name": "User",
        "is_active": True,
        "is_verified": True,
        "role": "free_user",
        "subscription_tier": "free",
    }


@pytest.fixture
def sample_chat_data():
    """Sample chat data for testing."""
    return {
        "id": "chat-123",
        "user_id": "user-123",
        "session_id": "session-123",
        "message": "Hello, world!",
        "response": "Hi there!",
        "graph_type": "todo",
        "frontend_type": "telegram",
    }


@pytest.fixture
def sample_subscription_data():
    """Sample subscription data for testing."""
    return {
        "id": "sub-123",
        "user_id": "user-123",
        "plan_id": "plan-basic",
        "tier": "basic",
        "is_active": True,
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-12-31T23:59:59Z",
    }


@pytest.fixture
def sample_graph_data():
    """Sample graph data for testing."""
    return {
        "id": "graph-123",
        "name": "ToDo Assistant",
        "graph_type": "todo",
        "description": "Task management assistant",
        "version": "1.0.0",
        "is_public": True,
        "status": "healthy",
    }


@pytest.fixture
def temp_config_file():
    """Temporary configuration file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as f:
        f.write("DATABASE_URL=sqlite:///test.db\n")
        f.write("REDIS_URL=redis://localhost:6379/15\n")
        f.write("JWT_PRIVATE_KEY=test_private_key\n")
        f.write("JWT_PUBLIC_KEY=test_public_key\n")
        temp_file = f.name

    yield temp_file

    # Cleanup
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest.fixture
def mock_jwt_payload():
    """Mock JWT payload for testing."""
    return {
        "sub": "user-123",
        "iss": "botspool.ai",
        "aud": "botspool-api",
        "iat": 1640995200,
        "exp": 1641081600,
        "type": "access",
        "role": "premium_user",
        "permissions": ["read_graphs", "write_graphs"],
        "frontend_type": "telegram",
        "allowed_graphs": ["todo", "email", "calendar"],
        "jti": "token-123",
    }


@pytest.fixture
def mock_error_context():
    """Mock error context for testing."""
    return {
        "request_id": "req-123",
        "user_id": "user-123",
        "session_id": "session-123",
        "conversation_id": "conv-123",
        "graph_type": "todo",
        "frontend_type": "telegram",
        "ip_address": "192.168.1.1",
        "user_agent": "TelegramBot/1.0",
        "endpoint": "/api/v1/chat/todo",
        "method": "POST",
        "timestamp": "2024-01-01T10:00:00Z",
    }
