"""
Database monitoring utilities for BotsPool

This module provides database monitoring capabilities including performance
monitoring, health checks, and metrics collection.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .connection import DatabaseManager, ConnectionPoolMonitor
from ..errors import DatabaseError


class QueryPerformanceMonitor:
    """
    Monitor for database query performance.
    """

    def __init__(self, database_manager: DatabaseManager):
        self.database_manager = database_manager
        self.logger = logging.getLogger(__name__)

        # Performance metrics
        self.query_times: List[float] = []
        self.slow_queries: List[Dict[str, Any]] = []
        self.query_counts: Dict[str, int] = {}

        # Configuration
        self.slow_query_threshold = 1.0  # seconds
        self.max_query_history = 1000

    async def monitor_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Monitor a query execution.

        Args:
            query: SQL query
            parameters: Query parameters

        Returns:
            Query result
        """
        start_time = time.time()

        try:
            result = await self.database_manager.execute_query(query, parameters)

            # Record performance metrics
            execution_time = time.time() - start_time
            await self._record_query_metrics(query, execution_time, True)

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            await self._record_query_metrics(query, execution_time, False, str(e))
            raise

    async def _record_query_metrics(
        self,
        query: str,
        execution_time: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record query performance metrics."""
        # Add to query times
        self.query_times.append(execution_time)
        if len(self.query_times) > self.max_query_history:
            self.query_times.pop(0)

        # Track slow queries
        if execution_time > self.slow_query_threshold:
            self.slow_queries.append(
                {
                    "query": query[:200],  # Truncate for storage
                    "execution_time": execution_time,
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": success,
                    "error": error,
                }
            )

            # Keep only recent slow queries
            if len(self.slow_queries) > 100:
                self.slow_queries.pop(0)

        # Count queries by type
        query_type = self._get_query_type(query)
        self.query_counts[query_type] = self.query_counts.get(query_type, 0) + 1

    def _get_query_type(self, query: str) -> str:
        """Get query type from SQL."""
        query_upper = query.strip().upper()

        if query_upper.startswith("SELECT"):
            return "SELECT"
        elif query_upper.startswith("INSERT"):
            return "INSERT"
        elif query_upper.startswith("UPDATE"):
            return "UPDATE"
        elif query_upper.startswith("DELETE"):
            return "DELETE"
        else:
            return "OTHER"

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get query performance metrics."""
        if not self.query_times:
            return {
                "total_queries": 0,
                "average_time": 0,
                "slow_queries": 0,
                "query_types": {},
            }

        return {
            "total_queries": len(self.query_times),
            "average_time": sum(self.query_times) / len(self.query_times),
            "min_time": min(self.query_times),
            "max_time": max(self.query_times),
            "slow_queries": len(self.slow_queries),
            "query_types": self.query_counts.copy(),
            "recent_slow_queries": self.slow_queries[-10:],  # Last 10 slow queries
        }

    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self.query_times.clear()
        self.slow_queries.clear()
        self.query_counts.clear()


class DatabaseMonitor:
    """
    Comprehensive database monitor for BotsPool.

    Monitors database health, performance, and provides alerts.
    """

    def __init__(self, database_manager: DatabaseManager):
        self.database_manager = database_manager
        self.logger = logging.getLogger(__name__)

        # Initialize sub-monitors
        self.pool_monitor = ConnectionPoolMonitor(database_manager)
        self.query_monitor = QueryPerformanceMonitor(database_manager)

        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task = None

        # Health check configuration
        self.health_check_interval = 60  # seconds
        self.performance_check_interval = 300  # seconds

        # Alert thresholds
        self.connection_pool_threshold = 90  # percentage
        self.slow_query_threshold = 1.0  # seconds
        self.error_rate_threshold = 5  # percentage

    async def start_monitoring(self) -> None:
        """Start database monitoring."""
        if self.is_monitoring:
            self.logger.warning("Database monitoring is already running")
            return

        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Database monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop database monitoring."""
        if not self.is_monitoring:
            return

        self.is_monitoring = False

        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Database monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Health check
                await self._perform_health_check()

                # Performance check
                await self._perform_performance_check()

                # Wait for next check
                await asyncio.sleep(self.health_check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(10)  # Wait before retrying

    async def _perform_health_check(self) -> None:
        """Perform database health check."""
        try:
            health_status = await self.database_manager.health_check()

            if health_status["status"] != "healthy":
                self.logger.warning(f"Database health check failed: {health_status}")
                await self._send_alert("database_health", health_status)

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            await self._send_alert("health_check_error", {"error": str(e)})

    async def _perform_performance_check(self) -> None:
        """Perform performance check."""
        try:
            # Check connection pool
            pool_health = await self.pool_monitor.check_pool_health()

            if pool_health["status"] != "healthy":
                self.logger.warning(f"Connection pool health issue: {pool_health}")
                await self._send_alert("pool_health", pool_health)

            # Check query performance
            perf_metrics = self.query_monitor.get_performance_metrics()

            if perf_metrics["average_time"] > self.slow_query_threshold:
                self.logger.warning(
                    f"Slow query performance: {perf_metrics['average_time']:.2f}s"
                )
                await self._send_alert("slow_queries", perf_metrics)

        except Exception as e:
            self.logger.error(f"Performance check failed: {e}")

    async def _send_alert(self, alert_type: str, data: Dict[str, Any]) -> None:
        """Send monitoring alert."""
        alert = {
            "type": alert_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }

        self.logger.warning(f"Database alert: {alert}")

        # Here you would integrate with your alerting system
        # (e.g., send to monitoring service, Slack, email, etc.)

    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive database status."""
        try:
            # Basic health check
            health_status = await self.database_manager.health_check()

            # Connection pool status
            pool_metrics = await self.pool_monitor.get_pool_metrics()
            pool_health = await self.pool_monitor.check_pool_health()

            # Query performance
            query_metrics = self.query_monitor.get_performance_metrics()

            # Database info
            db_info = await self._get_database_info()

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": self._determine_overall_status(
                    health_status, pool_health
                ),
                "health": health_status,
                "connection_pool": {"metrics": pool_metrics, "health": pool_health},
                "query_performance": query_metrics,
                "database_info": db_info,
                "monitoring": {
                    "is_active": self.is_monitoring,
                    "health_check_interval": self.health_check_interval,
                    "performance_check_interval": self.performance_check_interval,
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to get comprehensive status: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": "error",
                "error": str(e),
            }

    def _determine_overall_status(
        self, health_status: Dict[str, Any], pool_health: Dict[str, Any]
    ) -> str:
        """Determine overall database status."""
        if health_status.get("status") != "healthy":
            return "unhealthy"

        if pool_health.get("status") != "healthy":
            return "degraded"

        return "healthy"

    async def _get_database_info(self) -> Dict[str, Any]:
        """Get additional database information."""
        try:
            async with self.database_manager.get_session_context() as session:
                # Get table sizes
                table_sizes = await session.execute(
                    text(
                        """
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    LIMIT 10
                """
                    )
                )

                # Get connection info
                connections = await session.execute(
                    text(
                        """
                    SELECT 
                        state,
                        count(*) as count
                    FROM pg_stat_activity 
                    GROUP BY state
                """
                    )
                )

                return {
                    "table_sizes": [dict(row) for row in table_sizes.fetchall()],
                    "connections": [dict(row) for row in connections.fetchall()],
                }

        except Exception as e:
            self.logger.warning(f"Failed to get database info: {e}")
            return {"error": str(e)}

    async def reset_monitoring_metrics(self) -> None:
        """Reset all monitoring metrics."""
        self.query_monitor.reset_metrics()
        self.logger.info("Monitoring metrics reset")

    async def configure_monitoring(
        self,
        health_check_interval: Optional[int] = None,
        performance_check_interval: Optional[int] = None,
        slow_query_threshold: Optional[float] = None,
        connection_pool_threshold: Optional[int] = None,
    ) -> None:
        """Configure monitoring parameters."""
        if health_check_interval is not None:
            self.health_check_interval = health_check_interval

        if performance_check_interval is not None:
            self.performance_check_interval = performance_check_interval

        if slow_query_threshold is not None:
            self.slow_query_threshold = slow_query_threshold
            self.query_monitor.slow_query_threshold = slow_query_threshold

        if connection_pool_threshold is not None:
            self.connection_pool_threshold = connection_pool_threshold

        self.logger.info("Monitoring configuration updated")
