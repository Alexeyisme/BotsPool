"""Health check endpoints"""
from fastapi import APIRouter, Depends
from datetime import datetime
import redis.asyncio as redis

from ..config import settings

router = APIRouter()


async def get_redis_client():
    """Get Redis client"""
    client = redis.from_url(settings.REDIS_URL, decode_responses=False)
    try:
        yield client
    finally:
        await client.aclose()


@router.get("/health")
async def health_check(redis_client: redis.Redis = Depends(get_redis_client)):
    """
    Health check endpoint.

    Returns:
        Health status
    """
    # Check Redis
    try:
        await redis_client.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    return {
        "status": "healthy" if redis_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.SERVICE_NAME,
        "dependencies": {"redis": redis_status},
    }
