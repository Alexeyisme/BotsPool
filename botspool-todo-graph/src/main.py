"""
BotsPool ToDo Graph Service

FastAPI application for the ToDo graph service that integrates with
the BotsPool Core Gateway.
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from botspool_shared_utils.errors import BotsPoolError, ErrorCategory
from botspool_shared_utils.database import create_connection_pool, close_connection_pool
from botspool_shared_utils.langgraph import (
    create_postgres_checkpointer,
    close_postgres_checkpointer,
)
from .config import Settings, get_settings
from .api.endpoints import router as api_router
from .health.endpoints import router as health_router
from .services.gateway_registration import GatewayRegistrationService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()

    # Startup
    logger.info("Starting BotsPool ToDo Graph Service...")

    # Initialize PostgreSQL checkpointer for LangGraph
    checkpointer = None
    try:
        checkpointer = await create_postgres_checkpointer(settings.database_url)

        # Setup checkpointer - creates database tables if they don't exist
        # This is required the first time, and is idempotent
        logger.info("Setting up PostgreSQL checkpointer schema...")
        await checkpointer.setup()

        app.state.checkpointer = checkpointer
        logger.info("PostgreSQL checkpointer initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize PostgreSQL checkpointer: {e}")
        logger.info("Falling back to in-memory storage")
        app.state.checkpointer = None

    # Initialize shared-utils database manager
    try:
        await create_connection_pool(settings.database_url)
        logger.info("Database connection pool initialised")
    except Exception as exc:
        logger.warning(f"Database pool initialisation failed: {exc}")

    # Initialize gateway registration
    registration_service = GatewayRegistrationService(settings)
    await registration_service.start()

    # Store registration service in app state
    app.state.registration_service = registration_service

    logger.info("BotsPool ToDo Graph Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down BotsPool ToDo Graph Service...")

    # Close PostgreSQL checkpointer
    if checkpointer is not None:
        await close_postgres_checkpointer(checkpointer)

    # Stop gateway registration
    if hasattr(app.state, "registration_service"):
        await app.state.registration_service.stop()

    # Tear down database pool
    await close_connection_pool()

    logger.info("BotsPool ToDo Graph Service stopped")


# Create FastAPI application
app = FastAPI(
    title="BotsPool ToDo Graph Service",
    description="Specialized graph service for task management using LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

# Get settings
settings = get_settings()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://botspool.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(BotsPoolError)
async def botspool_error_handler(request: Request, exc: BotsPoolError) -> JSONResponse:
    """Handle BotsPool errors."""
    logger.error(f"BotsPool error: {exc}")

    # Map error categories to HTTP status codes
    status_code_map = {
        ErrorCategory.AUTHENTICATION: status.HTTP_401_UNAUTHORIZED,
        ErrorCategory.AUTHORIZATION: status.HTTP_403_FORBIDDEN,
        ErrorCategory.VALIDATION: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ErrorCategory.NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCategory.EXTERNAL_SERVICE: status.HTTP_502_BAD_GATEWAY,
        ErrorCategory.INTERNAL: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    status_code = status_code_map.get(
        exc.error_category, status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    error_response = exc.to_dict()

    return JSONResponse(status_code=status_code, content=error_response)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors."""
    logger.warning(f"Validation error: {exc}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Request validation failed",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
        },
    )


# Request middleware
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Request processing middleware."""
    import time
    import uuid

    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.time()

    logger.info(f"Request {request_id}: {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        processing_time = time.time() - start_time

        logger.info(
            f"Request {request_id} completed: {response.status_code} "
            f"in {processing_time:.3f}s"
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Processing-Time"] = str(processing_time)

        return response

    except Exception as exc:
        processing_time = time.time() - start_time
        logger.error(f"Request {request_id} failed: {exc} in {processing_time:.3f}s")
        raise


# Include routers
app.include_router(health_router)
app.include_router(api_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "BotsPool ToDo Graph Service",
        "version": "1.0.0",
        "status": "operational",
        "docs_url": "/docs" if settings.debug else None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
    )
