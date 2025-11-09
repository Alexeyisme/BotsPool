"""
Chat API endpoints for BotsPool Gateway

This module provides chat endpoints for communicating with graph instances
through the gateway's routing and load balancing system.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from botspool_shared_utils.models.enums import GraphType, FrontendType
from botspool_shared_utils.errors import ValidationError, AuthorizationError, ErrorCode
from botspool_shared_utils.auth.password_manager import PasswordManager

from ...auth.middleware import get_current_user_required, require_graph_access
from ...routing.router import GraphRouter, get_graph_router
from ...routing.load_balancer import LoadBalancingStrategy
from ...dependencies import (
    get_db_session,
    get_password_manager,
    get_jwt_handler,
    get_rbac_manager_dep,
    get_redis_client,
)
from ...services.user_service import UserService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/chat", tags=["Chat"])


# Request/Response Models
class ChatRequest(BaseModel):
    """Chat request model."""

    message: str = Field(
        ..., min_length=1, max_length=10000, description="User message"
    )
    session_id: Optional[str] = Field(None, description="Session identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Request context")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Request metadata")


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str = Field(..., description="Graph response")
    graph_type: str = Field(..., description="Graph type")
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    timestamp: str = Field(..., description="Response timestamp")
    instance_id: str = Field(..., description="Instance identifier")
    request_id: Optional[str] = Field(None, description="Request identifier")
    processing_time: Optional[float] = Field(
        None, description="Processing time in seconds"
    )
    routing_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Routing metadata"
    )


class ChatStreamResponse(BaseModel):
    """Chat streaming response model."""

    type: str = Field(..., description="Response type (start, chunk, end)")
    content: Optional[str] = Field(None, description="Response content")
    graph_type: str = Field(..., description="Graph type")
    session_id: str = Field(..., description="Session identifier")
    timestamp: str = Field(..., description="Response timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")


@router.post("/{graph_type}", response_model=ChatResponse)
async def chat_with_graph(
    graph_type: GraphType,
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    router: GraphRouter = Depends(get_graph_router),
    db_session: AsyncSession = Depends(get_db_session),
    password_manager: PasswordManager = Depends(get_password_manager),
    jwt_handler: Any = Depends(get_jwt_handler),
    rbac_manager: Any = Depends(get_rbac_manager_dep),
    redis_client: Any = Depends(get_redis_client),
):
    """
    Chat with a specific graph type.

    Routes the user's message to an appropriate instance of the specified
    graph type using load balancing and failover mechanisms.

    Args:
        graph_type: Type of graph to chat with
        request: Chat request data
        current_user: Current authenticated user
        router: Graph router instance
        db_session: Database session
        password_manager: Password manager
        jwt_handler: JWT handler
        rbac_manager: RBAC manager
        redis_client: Redis client

    Returns:
        ChatResponse: Response from the graph

    Raises:
        HTTPException: If chat fails
    """
    try:
        # Extract user information
        user_id = current_user.get("user_id")
        frontend_type = current_user.get("frontend_type", "api")

        # Check user permissions with database lookup
        user_service = UserService(
            db_session, password_manager, jwt_handler, rbac_manager, redis_client
        )
        await user_service.check_user_permissions(user_id, graph_type)

        # Route request to graph
        response = await router.route_request(
            graph_type=graph_type,
            message=request.message,
            user_id=user_id,
            session_id=request.session_id,
            context=request.context,
            metadata=request.metadata,
            frontend_type=FrontendType(frontend_type),
        )

        logger.info(
            f"Chat request processed for user {user_id} with {graph_type.value} graph"
        )

        return ChatResponse(**response)

    except ValidationError as exc:
        logger.warning(f"Chat request validation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        )

    except AuthorizationError as exc:
        logger.warning(f"Chat request authorization failed: {exc}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message)

    except Exception as exc:
        logger.error(f"Chat request failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat request failed",
        )


@router.post("/{graph_type}/stream")
async def stream_chat_with_graph(
    graph_type: GraphType,
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    router: GraphRouter = Depends(get_graph_router),
):
    """
    Stream chat with a specific graph type.

    Provides real-time streaming responses from the graph instance
    using Server-Sent Events (SSE).

    Args:
        graph_type: Type of graph to chat with
        request: Chat request data
        current_user: Current authenticated user
        router: Graph router instance

    Returns:
        StreamingResponse: Streamed response from the graph
    """
    try:
        # Extract user information
        user_id = current_user.get("user_id")
        frontend_type = current_user.get("frontend_type", "api")

        async def generate_stream():
            """Generate streaming response."""
            try:
                # Send start event
                yield f"data: {ChatStreamResponse(type='start', graph_type=graph_type.value, session_id=request.session_id or 'stream', timestamp='2024-01-01T00:00:00Z').json()}\n\n"

                # Route request to graph (this would be modified for streaming)
                response = await router.route_request(
                    graph_type=graph_type,
                    message=request.message,
                    user_id=user_id,
                    session_id=request.session_id,
                    context=request.context,
                    metadata=request.metadata,
                    frontend_type=FrontendType(frontend_type),
                )

                # Simulate streaming by chunking the response
                response_text = response.get("response", "")
                chunk_size = 50  # Characters per chunk

                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i : i + chunk_size]
                    stream_response = ChatStreamResponse(
                        type="chunk",
                        content=chunk,
                        graph_type=graph_type.value,
                        session_id=request.session_id or "stream",
                        timestamp="2024-01-01T00:00:00Z",
                    )
                    yield f"data: {stream_response.json()}\n\n"

                # Send end event
                end_response = ChatStreamResponse(
                    type="end",
                    graph_type=graph_type.value,
                    session_id=request.session_id or "stream",
                    timestamp="2024-01-01T00:00:00Z",
                    metadata=response.get("metadata", {}),
                )
                yield f"data: {end_response.json()}\n\n"

            except Exception as exc:
                logger.error(f"Streaming failed: {exc}")
                error_response = ChatStreamResponse(
                    type="error",
                    content=f"Streaming error: {str(exc)}",
                    graph_type=graph_type.value,
                    session_id=request.session_id or "stream",
                    timestamp="2024-01-01T00:00:00Z",
                )
                yield f"data: {error_response.json()}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            },
        )

    except Exception as exc:
        logger.error(f"Stream chat request failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stream chat request failed",
        )


@router.get("/{graph_type}/status")
async def get_chat_status(
    graph_type: GraphType,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    router: GraphRouter = Depends(get_graph_router),
):
    """
    Get chat status for a specific graph type.

    Returns information about available instances and routing status.

    Args:
        graph_type: Graph type to check
        current_user: Current authenticated user
        router: Graph router instance

    Returns:
        dict: Chat status information
    """
    try:
        # Get routing statistics
        routing_stats = router.get_routing_stats()

        # Get load balancer statistics
        load_balancer_stats = router.load_balancer.get_balancing_stats()

        # Get instance statistics
        instances = await router.registry.get_healthy_instances(graph_type)

        return {
            "graph_type": graph_type.value,
            "available_instances": len(instances),
            "routing_stats": routing_stats,
            "load_balancer_stats": {
                "strategy": router.load_balancer.strategy.value,
                "total_requests": load_balancer_stats.total_requests,
                "successful_requests": load_balancer_stats.successful_requests,
                "failed_requests": load_balancer_stats.failed_requests,
                "average_response_time": load_balancer_stats.average_response_time,
            },
            "instances": [
                {
                    "instance_id": inst.instance_id,
                    "endpoint": inst.endpoint,
                    "status": inst.status,
                    "capacity": inst.capacity,
                    "current_load": inst.current_load,
                    "version": inst.version,
                }
                for inst in instances
            ],
        }

    except Exception as exc:
        logger.error(f"Failed to get chat status: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat status",
        )


@router.get("/active-requests")
async def get_active_requests(
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    router: GraphRouter = Depends(get_graph_router),
):
    """
    Get list of active chat requests.

    Returns information about currently processing requests.
    Useful for monitoring and debugging.

    Args:
        current_user: Current authenticated user
        router: Graph router instance

    Returns:
        dict: Active requests information
    """
    try:
        active_requests = router.get_active_requests()

        return {
            "active_requests_count": len(active_requests),
            "active_requests": active_requests,
        }

    except Exception as exc:
        logger.error(f"Failed to get active requests: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active requests",
        )
