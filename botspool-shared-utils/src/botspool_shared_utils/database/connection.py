"""
Database connection management for BotsPool

This module provides database connection management, including connection pooling,
health checks, and connection utilities.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.pool.impl import AsyncAdaptedQueuePool

from ..errors import DatabaseConnectionError, DatabaseQueryError, ConfigurationError


class DatabaseManager:
    """
    Database connection manager for BotsPool.

    Manages database connections, connection pooling, and provides
    utilities for database operations.
    """

    def __init__(
        self,
        database_url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False,
    ):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo

        self.engine = None
        self.async_session_factory = None
        self._connection_pool = None
        self._is_connected = False

        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> None:
        """Initialize database connections and connection pool."""
        try:
            # Configure engine options per backend
            connect_args: Dict[str, Any] = {
                "command_timeout": 30,
                "server_settings": {
                    "application_name": "botspool",
                    "timezone": "UTC",
                },
            }
            pool_class = AsyncAdaptedQueuePool

            if self.database_url.startswith("sqlite"):
                connect_args = {}
                pool_class = NullPool

            engine_kwargs: Dict[str, Any] = {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_timeout": self.pool_timeout,
                "pool_recycle": self.pool_recycle,
                "echo": self.echo,
                "poolclass": pool_class,
                "connect_args": connect_args,
            }

            if pool_class is NullPool:
                engine_kwargs.pop("pool_size", None)
                engine_kwargs.pop("max_overflow", None)
                engine_kwargs.pop("pool_timeout", None)
                engine_kwargs.pop("pool_recycle", None)

            # Create async engine
            self.engine = create_async_engine(
                self.database_url,
                **engine_kwargs,
            )

            # Create session factory
            self.async_session_factory = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )

            # Test connection
            await self.test_connection()

            self._is_connected = True
            self.logger.info("Database connection initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
            raise DatabaseConnectionError(
                details={"database_url": self._mask_database_url(), "error": str(e)}
            )

    async def test_connection(self) -> bool:
        """Test database connection."""
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.logger.error(f"Database connection test failed: {e}")
            return False

    async def get_session(self) -> AsyncSession:
        """Get a database session."""
        if not self._is_connected:
            raise DatabaseConnectionError(details={"reason": "Database not connected"})

        return self.async_session_factory()

    @asynccontextmanager
    async def get_session_context(self):
        """Get a database session with automatic cleanup."""
        session = await self.get_session()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def get_transaction_context(self):
        """Get a database session with transaction management."""
        async with self.get_session_context() as session:
            async with session.begin():
                yield session

    async def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query.

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            List of result dictionaries
        """
        try:
            async with self.get_session_context() as session:
                result = await session.execute(text(query), parameters or {})

                if result.returns_rows:
                    columns = result.keys()
                    rows = result.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    return []

        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            raise DatabaseQueryError(
                f"Query execution failed: {e}",
                query=query,
                details={"parameters": parameters},
            )

    async def execute_scalar(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a scalar query (returns single value).

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            Scalar result
        """
        try:
            async with self.get_session_context() as session:
                result = await session.execute(text(query), parameters or {})
                return result.scalar()

        except Exception as e:
            self.logger.error(f"Scalar query execution failed: {e}")
            raise DatabaseQueryError(
                f"Scalar query execution failed: {e}",
                query=query,
                details={"parameters": parameters},
            )

    async def execute_many(
        self, query: str, parameters_list: List[Dict[str, Any]]
    ) -> None:
        """
        Execute a query multiple times with different parameters.

        Args:
            query: SQL query string
            parameters_list: List of parameter dictionaries
        """
        try:
            async with self.get_transaction_context() as session:
                for parameters in parameters_list:
                    await session.execute(text(query), parameters)

        except Exception as e:
            self.logger.error(f"Batch query execution failed: {e}")
            raise DatabaseQueryError(
                f"Batch query execution failed: {e}",
                query=query,
                details={"batch_size": len(parameters_list)},
            )

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check.

        Returns:
            Health check results
        """
        try:
            start_time = asyncio.get_event_loop().time()

            # Test basic connectivity
            await self.test_connection()

            # Get connection pool status
            pool_status = self._get_pool_status()

            # Get database info
            db_info = await self._get_database_info()

            end_time = asyncio.get_event_loop().time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds

            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "pool_status": pool_status,
                "database_info": db_info,
                "timestamp": asyncio.get_event_loop().time(),
            }

        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time(),
            }

    def _get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status."""
        if not self.engine:
            return {"status": "not_initialized"}

        pool = self.engine.pool
        try:
            return {
                "size": pool.size() if hasattr(pool, "size") else None,
                "checked_in": pool.checkedin() if hasattr(pool, "checkedin") else None,
                "checked_out": pool.checkedout()
                if hasattr(pool, "checkedout")
                else None,
                "overflow": pool.overflow() if hasattr(pool, "overflow") else None,
                "invalid": pool.invalid() if hasattr(pool, "invalid") else None,
            }
        except Exception as e:
            self.logger.warning(f"Could not get detailed pool status: {e}")
            return {"status": "active"}

    async def _get_database_info(self) -> Dict[str, Any]:
        """Get database information."""
        try:
            # Get database version
            version_query = "SELECT version()"
            version = await self.execute_scalar(version_query)

            # Get database size
            size_query = """
                SELECT pg_size_pretty(pg_database_size(current_database())) as size
            """
            size = await self.execute_scalar(size_query)

            # Get active connections
            connections_query = """
                SELECT count(*) as active_connections
                FROM pg_stat_activity
                WHERE state = 'active'
            """
            active_connections = await self.execute_scalar(connections_query)

            return {
                "version": version,
                "size": size,
                "active_connections": active_connections,
            }

        except Exception as e:
            self.logger.warning(f"Failed to get database info: {e}")
            return {"error": str(e)}

    def _mask_database_url(self) -> str:
        """Mask sensitive information in database URL."""
        try:
            parsed = urlparse(self.database_url)
            if parsed.password:
                masked_url = self.database_url.replace(parsed.password, "***")
                return masked_url
            return self.database_url
        except Exception:
            return "***"

    async def close(self) -> None:
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            self._is_connected = False
            self.logger.info("Database connections closed")

    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._is_connected


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


async def create_connection_pool(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    echo: bool = False,
) -> DatabaseManager:
    """
    Create and initialize a database connection pool.

    Args:
        database_url: Database connection URL
        pool_size: Connection pool size
        max_overflow: Maximum overflow connections
        pool_timeout: Connection timeout
        pool_recycle: Connection recycle time
        echo: Enable SQL logging

    Returns:
        Initialized DatabaseManager instance
    """
    global _database_manager

    _database_manager = DatabaseManager(
        database_url=database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        echo=echo,
    )

    await _database_manager.initialize()
    return _database_manager


def get_database_manager() -> DatabaseManager:
    """
    Get the global database manager instance.

    Returns:
        DatabaseManager instance

    Raises:
        ConfigurationError: If database manager is not initialized
    """
    global _database_manager

    if _database_manager is None:
        raise ConfigurationError("Database manager not initialized")

    return _database_manager


async def close_connection_pool() -> None:
    """Close the global database connection pool."""
    global _database_manager

    if _database_manager:
        await _database_manager.close()
        _database_manager = None


class ConnectionPoolMonitor:
    """
    Monitor for database connection pool health and performance.
    """

    def __init__(self, database_manager: DatabaseManager):
        self.database_manager = database_manager
        self.logger = logging.getLogger(__name__)

    async def get_pool_metrics(self) -> Dict[str, Any]:
        """Get connection pool metrics."""
        if not self.database_manager.is_connected():
            return {"status": "disconnected"}

        pool_status = self.database_manager._get_pool_status()

        # Calculate utilization
        total_connections = pool_status["size"] + pool_status["overflow"]
        used_connections = pool_status["checked_out"]
        utilization = (
            (used_connections / total_connections * 100) if total_connections > 0 else 0
        )

        return {
            "pool_size": pool_status["size"],
            "checked_in": pool_status["checked_in"],
            "checked_out": pool_status["checked_out"],
            "overflow": pool_status["overflow"],
            "invalid": pool_status["invalid"],
            "utilization_percent": utilization,
            "timestamp": asyncio.get_event_loop().time(),
        }

    async def check_pool_health(self) -> Dict[str, Any]:
        """Check connection pool health."""
        metrics = await self.get_pool_metrics()

        if metrics["status"] == "disconnected":
            return {"status": "unhealthy", "reason": "Database disconnected"}

        # Check for high utilization
        if metrics["utilization_percent"] > 90:
            return {
                "status": "degraded",
                "reason": f"High pool utilization: {metrics['utilization_percent']:.1f}%",
            }

        # Check for invalid connections
        if metrics["invalid"] > 0:
            return {
                "status": "degraded",
                "reason": f"Invalid connections: {metrics['invalid']}",
            }

        return {
            "status": "healthy",
            "utilization_percent": metrics["utilization_percent"],
        }
