"""
Health Check Endpoints for BotsPool ToDo Graph Service

Health monitoring and service status endpoints.
"""

import logging
import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends

from botspool_shared_utils.database.connection import get_database_manager
from botspool_shared_utils.redis_utils import RedisManager
from redis.asyncio import Redis
from botspool_shared_utils.errors import ConfigurationError
from ..config import Settings, get_settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Health"])


# Health check models
class HealthStatusResponse:
    """Health status response model."""

    def __init__(self, status: str, timestamp: str, services: Dict[str, Any]):
        self.status = status
        self.timestamp = timestamp
        self.services = services


# Dependency injection
def get_redis_manager(settings: Settings = Depends(get_settings)) -> RedisManager:
    """Get Redis manager instance."""
    redis_client = Redis.from_url(
        settings.redis_url,
        max_connections=settings.redis_max_connections,
        decode_responses=settings.redis_decode_responses,
        encoding="utf-8",
    )
    return RedisManager(redis_client=redis_client)


@router.get("/health")
async def get_health_status(
    settings: Settings = Depends(get_settings),
    redis_manager: RedisManager = Depends(get_redis_manager),
):
    """
    Get basic health status.

    Returns:
        Dict: Health status
    """
    try:
        # Check database connection
        db_status = {"status": "unavailable", "type": "postgresql"}
        try:
            db_manager = get_database_manager()
            health = await db_manager.health_check()
            db_status.update(health)
            db_status["status"] = (
                "healthy" if health.get("status") == "healthy" else "unhealthy"
            )
        except ConfigurationError as exc:
            logger.warning("Database manager not initialised: %s", exc)
            db_status["error"] = str(exc)
        except Exception as exc:
            logger.warning("Database health check failed: %s", exc)
            db_status["status"] = "unhealthy"
            db_status["error"] = str(exc)

        # Check Redis connection
        redis_healthy = False
        try:
            await redis_manager.redis_client.ping()
            redis_healthy = True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")

        # Determine overall status
        overall_status = (
            "healthy"
            if db_status["status"] == "healthy" and redis_healthy
            else "unhealthy"
        )

        return {
            "status": overall_status,
            "timestamp": time.time(),
            "services": {
                "database": db_status,
                "redis": {
                    "status": "healthy" if redis_healthy else "unhealthy",
                    "type": "redis",
                },
                "graph_service": {
                    "status": "healthy",
                    "type": "todo_graph",
                    "version": settings.app_version,
                },
            },
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed",
        )


@router.get("/health/status")
async def get_detailed_status(
    settings: Settings = Depends(get_settings),
    redis_manager: RedisManager = Depends(get_redis_manager),
):
    """
    Get detailed service status.

    Returns:
        Dict: Detailed status information
    """
    try:
        # Database status
        try:
            db_manager = get_database_manager()
            start_time = time.time()
            health = await db_manager.health_check()
            response_time = time.time() - start_time
            db_status = {
                "status": "healthy"
                if health.get("status") == "healthy"
                else "unhealthy",
                "response_time": response_time,
                **{k: v for k, v in health.items() if k not in {"status"}},
            }
        except ConfigurationError as exc:
            db_status = {"status": "unavailable", "error": str(exc), "response_time": 0}
        except Exception as exc:
            db_status = {"status": "unhealthy", "error": str(exc), "response_time": 0}

        # Redis status
        redis_status = {"status": "unknown", "response_time": 0}
        try:
            start_time = time.time()
            await redis_manager.redis_client.ping()
            redis_status = {
                "status": "healthy",
                "response_time": time.time() - start_time,
            }
        except Exception as e:
            redis_status = {"status": "unhealthy", "error": str(e), "response_time": 0}

        # System resources
        import psutil

        system_status = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }

        # Overall status
        overall_status = "healthy"
        if db_status["status"] != "healthy" or redis_status["status"] != "healthy":
            overall_status = "unhealthy"

        return {
            "status": overall_status,
            "timestamp": time.time(),
            "service_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "services": {
                "database": db_status,
                "redis": redis_status,
                "system": system_status,
            },
        }

    except Exception as e:
        logger.error(f"Detailed status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Detailed status check failed",
        )


@router.get("/health/ready")
async def readiness_check(
    settings: Settings = Depends(get_settings),
    redis_manager: RedisManager = Depends(get_redis_manager),
):
    """
    Readiness probe for Kubernetes.

    Returns:
        Dict: Readiness status
    """
    try:
        # Check if service is ready to accept requests
        ready = True
        issues = []

        # Check database
        try:
            db_manager = get_database_manager()
            async with db_manager.get_session_context() as session:
                await session.execute("SELECT 1")
        except ConfigurationError as exc:
            ready = False
            issues.append(f"Database not initialised: {exc}")
        except Exception as exc:
            ready = False
            issues.append(f"Database not ready: {exc}")

        # Check Redis
        try:
            await redis_manager.redis_client.ping()
        except Exception as e:
            ready = False
            issues.append(f"Redis not ready: {str(e)}")

        if ready:
            return {"status": "ready", "timestamp": time.time()}
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "not ready", "issues": issues},
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Readiness check failed",
        )


@router.get("/health/live")
async def liveness_check():
    """
    Liveness probe for Kubernetes.

    Returns:
        Dict: Liveness status
    """
    try:
        return {"status": "alive", "timestamp": time.time()}

    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Liveness check failed",
        )
