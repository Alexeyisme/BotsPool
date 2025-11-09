"""
BotsPool Database Utilities

This module provides database utilities for the BotsPool platform,
including connection management, ORM models, and query utilities.
"""

from .connection import (
    DatabaseManager,
    get_database_manager,
    create_connection_pool,
    close_connection_pool,
)

from .models import (
    Base,
    UserModel,
    UserAuthModel,
    UserProfileModel,
    UserPreferencesModel,
    UserSessionModel,
    ChatSessionModel,
    ChatMessageModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    UsageTrackingModel,
    GraphModel,
    GraphInstanceModel,
    GraphHealthModel,
    ToDoItemModel,
    ToDoProfileModel,
    ToDoInstructionModel,
    SessionRecordModel,
)

from .queries import (
    QueryBuilder,
    UserQueries,
    ChatQueries,
    SubscriptionQueries,
    GraphQueries,
    ToDoQueries,
    SessionQueries,
)

from .migrations import (
    MigrationManager,
    run_migrations,
    create_migration,
    rollback_migration,
)

from .monitoring import DatabaseMonitor, ConnectionPoolMonitor, QueryPerformanceMonitor

__all__ = [
    # Connection management
    "DatabaseManager",
    "get_database_manager",
    "create_connection_pool",
    "close_connection_pool",
    # ORM models
    "Base",
    "UserModel",
    "UserAuthModel",
    "UserProfileModel",
    "UserPreferencesModel",
    "UserSessionModel",
    "ChatSessionModel",
    "ChatMessageModel",
    "SubscriptionModel",
    "SubscriptionPlanModel",
    "UsageTrackingModel",
    "GraphModel",
    "GraphInstanceModel",
    "GraphHealthModel",
    "ToDoItemModel",
    "ToDoProfileModel",
    "ToDoInstructionModel",
    "SessionRecordModel",
    # Query utilities
    "QueryBuilder",
    "UserQueries",
    "ChatQueries",
    "SubscriptionQueries",
    "GraphQueries",
    "ToDoQueries",
    "SessionQueries",
    # Migration utilities
    "MigrationManager",
    "run_migrations",
    "create_migration",
    "rollback_migration",
    # Monitoring
    "DatabaseMonitor",
    "ConnectionPoolMonitor",
    "QueryPerformanceMonitor",
]
