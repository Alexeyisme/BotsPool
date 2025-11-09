"""Health check HTTP endpoint for monitoring"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx

app = FastAPI()

# These will be set from main.py
redis_client = None
settings = None


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""

    # Check Redis connection
    redis_healthy = False
    try:
        if redis_client:
            await redis_client.ping()
            redis_healthy = True
    except:
        pass

    # Check Gateway connection
    gateway_healthy = False
    try:
        if settings:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.GATEWAY_URL}/health/status", timeout=5.0
                )
                gateway_healthy = response.status_code == 200
    except:
        pass

    status = "healthy" if (redis_healthy and gateway_healthy) else "unhealthy"

    return JSONResponse(
        {
            "status": status,
            "service": "telegram-bot",
            "dependencies": {
                "redis": "healthy" if redis_healthy else "unhealthy",
                "gateway": "healthy" if gateway_healthy else "unhealthy",
            },
        }
    )


def set_dependencies(redis_cli, bot_settings):
    """Set dependencies for health check"""
    global redis_client, settings
    redis_client = redis_cli
    settings = bot_settings
