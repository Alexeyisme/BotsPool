"""
Health check endpoints for BotsPool Gateway

This module provides comprehensive health monitoring including:
- Basic health status
- Detailed system status
- Database connectivity
- Redis connectivity
- Service dependencies
- Kubernetes probes
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from botspool_shared_utils.database.monitoring import DatabaseMonitor
from botspool_shared_utils.redis_utils import RedisManager
from botspool_shared_utils.errors import DatabaseError, ExternalServiceError

from ..dependencies import get_database_manager, get_redis_client
from ..config import get_settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/health", tags=["Health"])

# Global health state
_startup_time = time.time()
_health_state: Dict[str, Any] = {}


class HealthResponse(BaseModel):
    """Basic health response model."""

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    uptime: float = Field(..., description="Service uptime in seconds")
    version: str = Field(..., description="Application version")


class DetailedHealthResponse(BaseModel):
    """Detailed health response model."""

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    uptime: float = Field(..., description="Service uptime in seconds")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    dependencies: Dict[str, Dict[str, Any]] = Field(
        ..., description="Dependency health status"
    )
    system: Dict[str, Any] = Field(..., description="System information")


class DependencyHealth(BaseModel):
    """Individual dependency health model."""

    status: str = Field(..., description="Dependency status")
    response_time: Optional[float] = Field(None, description="Response time in seconds")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    last_check: datetime = Field(
        default_factory=datetime.utcnow, description="Last check timestamp"
    )


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.

    Returns basic service health information.
    Used for simple health monitoring and load balancer checks.

    Returns:
        HealthResponse: Basic health information
    """
    uptime = time.time() - _startup_time
    settings = get_settings()

    return HealthResponse(status="healthy", uptime=uptime, version=settings.app_version)


@router.get("/status", response_model=DetailedHealthResponse)
async def detailed_health_check(
    db_manager=Depends(get_database_manager), redis_client=Depends(get_redis_client)
):
    """
    Detailed health check endpoint.

    Provides comprehensive health information including:
    - Service status and uptime
    - Database connectivity
    - Redis connectivity
    - System information

    Returns:
        DetailedHealthResponse: Detailed health information
    """
    settings = get_settings()
    uptime = time.time() - _startup_time

    # Check dependencies
    dependencies = await _check_dependencies(db_manager, redis_client)

    # Determine overall status
    overall_status = "healthy"
    for dep_name, dep_health in dependencies.items():
        if dep_health["status"] != "healthy":
            overall_status = "degraded"
            break

    # Get system information
    system_info = await _get_system_info()

    return DetailedHealthResponse(
        status=overall_status,
        uptime=uptime,
        version=settings.app_version,
        environment=settings.environment,
        dependencies=dependencies,
        system=system_info,
    )


@router.get("/ready")
async def readiness_probe():
    """
    Kubernetes readiness probe endpoint.

    Indicates if the service is ready to receive traffic.
    Returns 200 if ready, 503 if not ready.

    Returns:
        dict: Readiness status
    """
    try:
        # Check if critical dependencies are available
        # For now, just return ready if the service is running
        return {"status": "ready", "timestamp": datetime.utcnow()}
    except Exception as exc:
        logger.error(f"Readiness check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "error": str(exc)},
        )


@router.get("/live")
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.

    Indicates if the service is alive and should not be restarted.
    Returns 200 if alive, 503 if dead.

    Returns:
        dict: Liveness status
    """
    try:
        # Basic liveness check - service is alive if it can respond
        uptime = time.time() - _startup_time
        return {"status": "alive", "uptime": uptime, "timestamp": datetime.utcnow()}
    except Exception as exc:
        logger.error(f"Liveness check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "dead", "error": str(exc)},
        )


async def _check_dependencies(db_manager, redis_client) -> Dict[str, Dict[str, Any]]:
    """
    Check health of all dependencies.

    Args:
        db_manager: Database manager
        redis_client: Redis client

    Returns:
        Dict[str, Dict[str, Any]]: Dependency health status
    """
    dependencies = {}

    # Check database
    try:
        start_time = time.time()
        db_health = await db_manager.health_check()
        response_time = time.time() - start_time

        dependencies["database"] = {
            "status": "healthy"
            if db_health.get("status") == "healthy"
            else "unhealthy",
            "response_time": response_time,
            "details": db_health,
            "last_check": datetime.utcnow(),
        }
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        dependencies["database"] = {
            "status": "unhealthy",
            "error": str(exc),
            "last_check": datetime.utcnow(),
        }

    # Check Redis
    try:
        start_time = time.time()
        await redis_client.ping()
        response_time = time.time() - start_time

        dependencies["redis"] = {
            "status": "healthy",
            "response_time": response_time,
            "last_check": datetime.utcnow(),
        }
    except Exception as exc:
        logger.error(f"Redis health check failed: {exc}")
        dependencies["redis"] = {
            "status": "unhealthy",
            "error": str(exc),
            "last_check": datetime.utcnow(),
        }

    return dependencies


async def _get_system_info() -> Dict[str, Any]:
    """
    Get system information for health status.

    Returns:
        Dict[str, Any]: System information
    """
    import platform

    try:
        import psutil
    except ImportError:
        logger.warning("psutil not installed, system info will be limited")
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "note": "System metrics unavailable - psutil not installed",
        }

    try:
        # Get memory usage
        memory = psutil.virtual_memory()

        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Get disk usage
        disk = psutil.disk_usage("/")

        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
            },
            "cpu": {"percent": cpu_percent, "count": psutil.cpu_count()},
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100,
            },
        }
    except Exception as exc:
        logger.warning(f"Failed to get system info: {exc}")
        return {
            "error": "Unable to retrieve system information",
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        }


# Health state management
def update_health_state(key: str, value: Any):
    """Update global health state."""
    global _health_state
    _health_state[key] = value


def get_health_state() -> Dict[str, Any]:
    """Get current health state."""
    return _health_state.copy()


def reset_health_state():
    """Reset health state."""
    global _health_state
    _health_state = {}
