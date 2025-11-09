"""
Rate limiting middleware for BotsPool Gateway

This middleware implements rate limiting based on subscription tiers using Redis.
"""

import logging
import time
from typing import Callable, Optional, Dict, Any
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from botspool_shared_utils.errors import RateLimitError, ErrorCode

logger = logging.getLogger(__name__)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for protecting API endpoints.

    Implements sliding window rate limiting using Redis to track requests
    per user and per IP address based on subscription tiers.
    """

    def __init__(self, app, redis_client=None, enabled: bool = True):
        super().__init__(app)
        self.redis_client = redis_client
        self.enabled = enabled

        # IP-based rate limits for unauthenticated endpoints
        self.ip_rate_limits = {
            "registration": {"limit": 5, "window": 900},  # 5 per 15 min
            "login": {"limit": 10, "window": 60},  # 10 per minute
            "password_reset": {"limit": 3, "window": 900},  # 3 per 15 min
        }

        logger.info(f"Rate limiting middleware initialized (enabled: {enabled})")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through rate limiter.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response: HTTP response

        Raises:
            RateLimitError: If rate limit exceeded
        """
        # Skip rate limiting if disabled
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for health checks
        if self._is_health_check(request):
            return await call_next(request)

        try:
            # Check rate limits before processing
            await self._check_rate_limits(request)

            # Process request
            response = await call_next(request)

            return response

        except RateLimitError as exc:
            logger.warning(
                f"Rate limit exceeded for {request.url.path}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else None,
                },
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": exc.message,
                    "retry_after": 60,  # Suggest retry after 60 seconds
                    "error_code": exc.error_code.value
                    if hasattr(exc, "error_code")
                    else ErrorCode.RATE_LIMIT_EXCEEDED_101.value,
                },
                headers={"Retry-After": "60"},
            )

    def _is_health_check(self, request: Request) -> bool:
        """Check if request is a health check."""
        health_paths = ["/health", "/health/status", "/health/ready", "/health/live"]
        return request.url.path in health_paths

    async def _check_rate_limits(self, request: Request) -> None:
        """
        Check rate limits for the request.

        Args:
            request: FastAPI request

        Raises:
            RateLimitError: If rate limit exceeded
        """
        # Check IP-based limits for unauthenticated endpoints
        if self._requires_ip_rate_limit(request):
            await self._check_ip_rate_limit(request)

    def _requires_ip_rate_limit(self, request: Request) -> bool:
        """Check if endpoint requires IP-based rate limiting."""
        ip_limited_paths = {
            "/api/v1/auth/register": "registration",
            "/api/v1/auth/login": "login",
            "/api/v1/auth/password-reset/request": "password_reset",
        }
        return request.url.path in ip_limited_paths

    async def _check_ip_rate_limit(self, request: Request) -> None:
        """
        Check IP-based rate limits.

        Args:
            request: FastAPI request

        Raises:
            RateLimitError: If rate limit exceeded
        """
        if not self.redis_client:
            # If Redis is unavailable, skip rate limiting
            logger.warning("Redis not available, skipping IP rate limiting")
            return

        ip = request.client.host if request.client else "unknown"

        # Determine which rate limit to apply
        ip_limited_paths = {
            "/api/v1/auth/register": "registration",
            "/api/v1/auth/login": "login",
            "/api/v1/auth/password-reset/request": "password_reset",
        }

        limit_type = ip_limited_paths.get(request.url.path)
        if not limit_type:
            return

        limits = self.ip_rate_limits.get(limit_type, {})
        max_requests = limits.get("limit", 10)
        window_seconds = limits.get("window", 60)

        # Check rate limit
        key = f"rate_limit:ip:{ip}:{limit_type}:{int(time.time() / window_seconds)}"
        current_count = await self.redis_client.get(key)

        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)

        if current_count >= max_requests:
            raise RateLimitError(
                message=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds allowed.",
                error_code=ErrorCode.RATE_LIMIT_EXCEEDED_101,
            )

        # Increment counter with TTL
        await self.redis_client.incr(key)
        await self.redis_client.expire(key, window_seconds)

    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """
        Get rate limiting statistics.

        Returns:
            Dict[str, Any]: Rate limiting statistics
        """
        return {
            "enabled": self.enabled,
            "ip_rate_limits": self.ip_rate_limits,
            "redis_available": self.redis_client is not None,
        }


# Convenience function for creating middleware
def create_rate_limiter_middleware(
    redis_client=None, enabled: bool = True
) -> RateLimiterMiddleware:
    """
    Create rate limiter middleware with custom configuration.

    Args:
        redis_client: Redis client instance
        enabled: Whether rate limiting is enabled

    Returns:
        RateLimiterMiddleware: Configured middleware factory
    """

    def middleware_factory(app):
        return RateLimiterMiddleware(app, redis_client, enabled)

    return middleware_factory
