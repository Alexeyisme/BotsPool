"""
Test fixtures for botspool-shared-utils
"""

from .data import (
    sample_user_data,
    sample_chat_data,
    sample_subscription_data,
    sample_graph_data,
    sample_error_data,
)

from .database import (
    create_test_database,
    cleanup_test_database,
    insert_test_data,
    get_test_connection,
)

from .redis import (
    create_test_redis,
    cleanup_test_redis,
    insert_test_redis_data,
    get_test_redis_client,
)

from .mocks import (
    mock_redis_client,
    mock_database_connection,
    mock_jwt_handler,
    mock_password_manager,
)

__all__ = [
    # Data fixtures
    "sample_user_data",
    "sample_chat_data",
    "sample_subscription_data",
    "sample_graph_data",
    "sample_error_data",
    # Database fixtures
    "create_test_database",
    "cleanup_test_database",
    "insert_test_data",
    "get_test_connection",
    # Redis fixtures
    "create_test_redis",
    "cleanup_test_redis",
    "insert_test_redis_data",
    "get_test_redis_client",
    # Mock fixtures
    "mock_redis_client",
    "mock_database_connection",
    "mock_jwt_handler",
    "mock_password_manager",
]
