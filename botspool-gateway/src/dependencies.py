"""
Dependency injection for FastAPI endpoints

This module provides reusable dependencies for database connections,
Redis clients, configuration, and other shared resources.
"""

import logging
from typing import AsyncGenerator, Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

from botspool_shared_utils.database.connection import DatabaseManager
from botspool_shared_utils.auth.jwt_handler import (
    JWTHandler,
    get_jwt_handler as get_jwt_handler_shared,
)
from botspool_shared_utils.auth.rbac import RBACManager, get_rbac_manager
from botspool_shared_utils.auth.password_manager import PasswordManager
from botspool_shared_utils.redis_utils import RedisManager

from .config import Settings, get_settings


# Global instances
_db_manager: Optional[DatabaseManager] = None
_redis_client: Optional[Redis] = None
_redis_manager: Optional[RedisManager] = None
_password_manager: Optional[PasswordManager] = None


async def get_database_manager() -> DatabaseManager:
    """
    Get the database manager instance.

    Returns:
        DatabaseManager: Database manager
    """
    global _db_manager

    if _db_manager is None:
        settings = get_settings()
        _db_manager = DatabaseManager(
            database_url=settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            echo=settings.debug,
        )
        try:
            await _db_manager.initialize()
        except Exception as e:
            logger.warning(
                f"Database initialization failed: {e}. Continuing without database connection."
            )
            # Don't raise the exception, allow the app to start without database

    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.

    Yields:
        AsyncSession: Database session
    """
    db_manager = await get_database_manager()
    async with db_manager.get_session_context() as session:
        yield session


async def get_redis_client() -> Redis:
    """
    Get Redis client instance.

    Returns:
        Redis: Redis client
    """
    global _redis_client

    if _redis_client is None:
        settings = get_settings()
        _redis_client = Redis.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=settings.redis_decode_responses,
            encoding="utf-8",
        )

    return _redis_client


def get_jwt_handler() -> JWTHandler:
    """
    Get JWT handler instance.

    Returns:
        JWTHandler: JWT handler
    """
    return get_jwt_handler_shared()


def get_rbac_manager_dep() -> RBACManager:
    """
    Get RBAC manager instance for dependency injection.

    Returns:
        RBACManager: RBAC manager
    """
    return get_rbac_manager()


def get_password_manager() -> PasswordManager:
    """
    Get password manager instance for dependency injection.

    Returns:
        PasswordManager: Password manager
    """
    global _password_manager

    if _password_manager is None:
        _password_manager = PasswordManager(rounds=12)

    return _password_manager


def get_user_service_factory(
    session: AsyncSession,
    password_manager: PasswordManager,
    jwt_handler: JWTHandler,
    rbac_manager: RBACManager,
    redis_client: Redis,
) -> "UserService":
    """
    Factory function to create UserService instance.

    Args:
        session: Database session
        password_manager: Password manager
        jwt_handler: JWT handler
        rbac_manager: RBAC manager
        redis_client: Redis client

    Returns:
        UserService: User service instance
    """
    from .services.user_service import UserService

    return UserService(
        session, password_manager, jwt_handler, rbac_manager, redis_client
    )


async def get_redis_manager() -> RedisManager:
    """
    Get Redis manager instance.

    Returns:
        RedisManager: Redis manager
    """
    global _redis_manager, _redis_client

    if _redis_manager is None:
        settings = get_settings()
        if _redis_client is None:
            _redis_client = Redis.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                decode_responses=settings.redis_decode_responses,
                encoding="utf-8",
            )
        _redis_manager = RedisManager(_redis_client)

    return _redis_manager


async def get_graph_registry():
    """Get graph registry instance."""
    from ..graphs.registry import get_graph_registry

    return get_graph_registry()


async def get_load_balancer():
    """Get load balancer instance."""
    from ..routing.load_balancer import get_load_balancer

    return get_load_balancer()


async def get_graph_router():
    """Get graph router instance."""
    from ..routing.router import get_graph_router

    return get_graph_router()


async def cleanup_resources():
    """
    Cleanup global resources.

    Should be called on application shutdown.
    """
    global _db_manager, _redis_client, _redis_manager

    # Close database connections
    if _db_manager is not None:
        await _db_manager.close()
        _db_manager = None

    # Close Redis connection
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
    _redis_manager = None
