"""
Test data fixtures for botspool-shared-utils
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import uuid


def sample_user_data() -> Dict[str, Any]:
    """Sample user data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "username": "testuser",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8KzKz2O",
        "first_name": "Test",
        "last_name": "User",
        "is_active": True,
        "is_verified": True,
        "role": "free_user",
        "subscription_tier": "free",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


def sample_chat_data() -> Dict[str, Any]:
    """Sample chat data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "message": "Hello, world!",
        "response": "Hi there!",
        "graph_type": "todo",
        "frontend_type": "telegram",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


def sample_subscription_data() -> Dict[str, Any]:
    """Sample subscription data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "plan_id": "plan-basic",
        "tier": "basic",
        "is_active": True,
        "start_date": datetime.utcnow().isoformat(),
        "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


def sample_graph_data() -> Dict[str, Any]:
    """Sample graph data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "name": "ToDo Assistant",
        "graph_type": "todo",
        "description": "Task management assistant",
        "version": "1.0.0",
        "is_public": True,
        "status": "healthy",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


def sample_error_data() -> Dict[str, Any]:
    """Sample error data for testing."""
    return {
        "error_code": "AUTH_INVALID_CREDENTIALS_100",
        "message": "Invalid credentials",
        "severity": "high",
        "category": "authentication",
        "details": {"field": "password"},
        "retryable": False,
        "retry_after_seconds": None,
        "timestamp": datetime.utcnow().isoformat(),
    }


def sample_user_list(count: int = 5) -> List[Dict[str, Any]]:
    """Generate a list of sample users."""
    users = []
    for i in range(count):
        user = sample_user_data()
        user["email"] = f"test{i}@example.com"
        user["username"] = f"testuser{i}"
        users.append(user)
    return users


def sample_chat_list(count: int = 5) -> List[Dict[str, Any]]:
    """Generate a list of sample chats."""
    chats = []
    for i in range(count):
        chat = sample_chat_data()
        chat["message"] = f"Test message {i}"
        chat["response"] = f"Test response {i}"
        chats.append(chat)
    return chats


def sample_subscription_list(count: int = 5) -> List[Dict[str, Any]]:
    """Generate a list of sample subscriptions."""
    subscriptions = []
    for i in range(count):
        subscription = sample_subscription_data()
        subscription["tier"] = ["free", "basic", "premium", "enterprise"][i % 4]
        subscriptions.append(subscription)
    return subscriptions


def sample_graph_list(count: int = 5) -> List[Dict[str, Any]]:
    """Generate a list of sample graphs."""
    graphs = []
    graph_types = ["todo", "email", "calendar", "document", "code"]
    for i in range(count):
        graph = sample_graph_data()
        graph["name"] = f"Test Graph {i}"
        graph["graph_type"] = graph_types[i % len(graph_types)]
        graphs.append(graph)
    return graphs


def sample_error_list(count: int = 5) -> List[Dict[str, Any]]:
    """Generate a list of sample errors."""
    errors = []
    error_codes = [
        "AUTH_INVALID_CREDENTIALS_100",
        "AUTH_TOKEN_EXPIRED_101",
        "VALIDATION_SCHEMA_ERROR_300",
        "GRAPH_EXECUTION_FAILED_400",
        "DB_CONNECTION_FAILED_500",
    ]
    for i in range(count):
        error = sample_error_data()
        error["error_code"] = error_codes[i % len(error_codes)]
        error["message"] = f"Test error {i}"
        errors.append(error)
    return errors


def sample_jwt_payload() -> Dict[str, Any]:
    """Sample JWT payload for testing."""
    return {
        "sub": str(uuid.uuid4()),
        "iss": "botspool.ai",
        "aud": "botspool-api",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        "type": "access",
        "role": "premium_user",
        "permissions": ["read_graphs", "write_graphs"],
        "frontend_type": "telegram",
        "allowed_graphs": ["todo", "email", "calendar"],
        "jti": str(uuid.uuid4()),
    }


def sample_error_context() -> Dict[str, Any]:
    """Sample error context for testing."""
    return {
        "request_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "conversation_id": str(uuid.uuid4()),
        "graph_type": "todo",
        "frontend_type": "telegram",
        "ip_address": "192.168.1.1",
        "user_agent": "TelegramBot/1.0",
        "endpoint": "/api/v1/chat/todo",
        "method": "POST",
        "timestamp": datetime.utcnow().isoformat(),
    }


def sample_encryption_data() -> Dict[str, Any]:
    """Sample encryption data for testing."""
    return {
        "plaintext": "This is a test message",
        "key": "test_key_32_bytes_long_123456",
        "salt": "test_salt_16_bytes",
        "iv": "test_iv_12_bytes",
        "auth_tag": "test_tag_16_bytes",
    }


def sample_performance_metrics() -> Dict[str, Any]:
    """Sample performance metrics for testing."""
    return {
        "execution_time_ms": 150.5,
        "memory_usage_mb": 45.2,
        "cpu_usage_percent": 12.3,
        "database_queries": 5,
        "cache_hits": 3,
        "cache_misses": 2,
        "timestamp": datetime.utcnow().isoformat(),
    }
