"""
BotsPool Gateway - Main Application

This is the core API gateway for the BotsPool platform, providing authentication,
routing, and orchestration for multiple AI graph services.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from botspool_shared_utils.errors import (
    BotsPoolError,
    ErrorCategory,
    ErrorSeverity,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    DatabaseError,
    ExternalServiceError,
    RateLimitError,
    ConfigurationError,
)
from botspool_shared_utils.logging.config import setup_logging

from .config import get_settings
from .dependencies import cleanup_resources
from .middleware.circuit_breaker import CircuitBreakerMiddleware
from .middleware.rate_limiter import RateLimiterMiddleware


# Initialize settings and logging
settings = get_settings()
setup_logging(level=settings.log_level, environment=settings.environment)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    # Initialize JWT handler first
    try:
        from botspool_shared_utils.auth.jwt_handler import create_jwt_handler

        create_jwt_handler(
            private_key=settings.jwt_private_key,
            public_key=settings.jwt_public_key,
            algorithm=settings.jwt_algorithm,
            access_token_expiry=settings.jwt_access_token_expiry,
            refresh_token_expiry=settings.jwt_refresh_token_expiry,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
        logger.info("JWT handler initialized")
    except Exception as exc:
        logger.error(f"JWT handler initialization failed: {exc}")

    # Initialize graph registry (Redis-backed) and routing components
    try:
        # Explicitly create registry to avoid lazy import issues
        from .dependencies import get_redis_manager, get_rbac_manager_dep
        from .graphs.registry import create_graph_registry
        from .routing.load_balancer import create_load_balancer, get_load_balancer
        from .routing.router import create_graph_router

        redis_manager = await get_redis_manager()
        create_graph_registry(redis_manager)
        logger.info("Graph registry initialized")

        # Initialize load balancer
        registry = __import__(
            "src.graphs.registry", fromlist=["get_graph_registry"]
        ).get_graph_registry()
        create_load_balancer(registry=registry)

        # Initialize graph router
        rbac_manager = get_rbac_manager_dep()
        load_balancer = __import__(
            "src.routing.load_balancer", fromlist=["get_load_balancer"]
        ).get_load_balancer()
        create_graph_router(
            load_balancer=load_balancer, registry=registry, rbac_manager=rbac_manager
        )
        logger.info("Routing components initialized")
    except Exception as exc:
        logger.warning(f"Graph registry initialization failed: {exc}")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await cleanup_resources()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Core API Gateway for BotsPool platform - Authentication, routing, and orchestration",
    lifespan=lifespan,
    debug=settings.debug,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Add trusted host middleware for production
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["*.botspool.ai", "botspool.ai"]
    )

# Add rate limiting middleware
app.add_middleware(
    RateLimiterMiddleware,
    redis_client=None,  # Will be set dynamically if available
    enabled=settings.rate_limit_enabled,
)

# Add circuit breaker middleware for fault tolerance
app.add_middleware(CircuitBreakerMiddleware)


# Request ID and logging middleware
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """
    Add request ID and enhanced logging middleware.

    This middleware:
    - Generates a unique request ID for tracing
    - Logs request/response with structured data
    - Tracks processing time
    - Handles errors gracefully
    """
    import time
    import uuid

    # Generate unique request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Start timing
    start_time = time.time()

    # Log incoming request
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
        },
    )

    try:
        # Process request
        response = await call_next(request)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Log successful response
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "processing_time": round(processing_time, 3),
                "response_size": response.headers.get("content-length"),
            },
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    except Exception as exc:
        # Calculate processing time for failed requests
        processing_time = time.time() - start_time

        # Log failed request
        logger.error(
            f"Request failed: {request.method} {request.url.path} - {type(exc).__name__}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "processing_time": round(processing_time, 3),
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            },
            exc_info=True,
        )

        # Re-raise the exception to be handled by error handlers
        raise


# Global exception handler for BotsPoolError
@app.exception_handler(BotsPoolError)
async def botspool_error_handler(request: Request, exc: BotsPoolError) -> JSONResponse:
    """
    Handle all BotsPool-specific errors.

    Args:
        request: FastAPI request
        exc: BotsPool error

    Returns:
        JSONResponse: Error response
    """
    # Add request context to error
    exc.request_id = getattr(request.state, "request_id", None)

    # Log error based on severity with structured logging
    log_extra = {
        "error_code": exc.error_code.value if exc.error_code else "UNKNOWN",
        "category": exc.error_category.value if exc.error_category else "UNKNOWN",
        "severity": exc.severity.value if exc.severity else "MEDIUM",
        "path": request.url.path,
        "method": request.method,
        "user_id": exc.user_id,
        "request_id": exc.request_id,
        "retryable": exc.retryable,
        "client_ip": request.client.host if request.client else None,
    }

    if exc.severity == ErrorSeverity.CRITICAL:
        logger.error(f"Critical error: {exc.message}", extra=log_extra, exc_info=True)
    elif exc.severity == ErrorSeverity.HIGH:
        logger.error(f"High severity error: {exc.message}", extra=log_extra)
    elif exc.severity == ErrorSeverity.MEDIUM:
        logger.warning(f"Medium severity error: {exc.message}", extra=log_extra)
    else:
        logger.info(f"Low severity error: {exc.message}", extra=log_extra)

    # Map error category to HTTP status code
    status_code_map = {
        ErrorCategory.AUTHENTICATION: status.HTTP_401_UNAUTHORIZED,
        ErrorCategory.AUTHORIZATION: status.HTTP_403_FORBIDDEN,
        ErrorCategory.VALIDATION: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ErrorCategory.GRAPH: status.HTTP_404_NOT_FOUND,
        ErrorCategory.SUBSCRIPTION: status.HTTP_409_CONFLICT,
        ErrorCategory.RATE_LIMIT: status.HTTP_429_TOO_MANY_REQUESTS,
        ErrorCategory.EXTERNAL_SERVICE: status.HTTP_503_SERVICE_UNAVAILABLE,
        ErrorCategory.DATABASE: status.HTTP_503_SERVICE_UNAVAILABLE,
        ErrorCategory.CONFIGURATION: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCategory.INTERNAL: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    status_code = status_code_map.get(
        exc.error_category, status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    # Use the error's built-in to_dict method for consistent formatting
    error_response = exc.to_dict()

    # Add retry headers if applicable
    headers = {}
    if exc.retryable and exc.retry_after_seconds:
        headers["Retry-After"] = str(exc.retry_after_seconds)

    return JSONResponse(
        status_code=status_code, content=error_response, headers=headers
    )


# Global exception handler for unexpected errors
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unexpected errors.

    Args:
        request: FastAPI request
        exc: Exception

    Returns:
        JSONResponse: Error response
    """
    # Create a BotsPoolError from the unexpected exception
    from botspool_shared_utils.errors import ErrorCode

    botspool_error = BotsPoolError(
        message=str(exc) if settings.is_development else "An internal error occurred",
        error_code=ErrorCode.INTERNAL_SERVER_ERROR_001,
        error_category=ErrorCategory.INTERNAL,
        severity=ErrorSeverity.CRITICAL,
        details={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
        retryable=False,
    )

    # Use the same handler as BotsPoolError
    return await botspool_error_handler(request, botspool_error)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.

    Returns:
        dict: API information
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "operational",
        "docs_url": "/docs" if settings.is_development else None,
    }


# Import and include routers
from .health.endpoints import router as health_router
from .api.v1.auth import router as auth_router
from .api.v1.graphs import router as graphs_router
from .api.v1.chat import router as chat_router

# Include routers
app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(graphs_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        workers=settings.workers if not settings.is_development else 1,
        log_level=settings.log_level.lower(),
    )
