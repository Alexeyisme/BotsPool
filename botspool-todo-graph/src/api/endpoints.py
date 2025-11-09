"""
API Endpoints for BotsPool ToDo Graph Service

FastAPI endpoints for task management operations.
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, Field

from botspool_shared_utils.errors import ValidationError, AuthorizationError, ErrorCode
from ..services.todo_service import ToDoService
from ..config import Settings, get_settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["ToDo Graph"])


# Request/Response Models
class ChatRequest(BaseModel):
    """Chat request model."""

    message: str = Field(
        ..., min_length=1, max_length=10000, description="User message"
    )
    session_id: Optional[str] = Field(None, description="Session identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Request context")


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str = Field(..., description="Agent response")
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    timestamp: str = Field(..., description="Response timestamp")
    graph_type: str = Field(..., description="Graph type")
    memory_stats: Dict[str, Any] = Field(..., description="Memory statistics")
    metadata: Dict[str, Any] = Field(..., description="Response metadata")


class ToDoRequest(BaseModel):
    """ToDo request model."""

    task: str = Field(
        ..., min_length=1, max_length=1000, description="Task description"
    )
    time_to_complete: Optional[int] = Field(
        None, description="Estimated time to complete (minutes)"
    )
    deadline: Optional[str] = Field(None, description="Deadline (ISO format)")
    solutions: List[str] = Field(
        default_factory=list, description="Actionable solutions"
    )
    status: str = Field(default="not started", description="Task status")


class ToDoResponse(BaseModel):
    """ToDo response model."""

    todo_id: str = Field(..., description="ToDo identifier")
    user_id: str = Field(..., description="User identifier")
    task: str = Field(..., description="Task description")
    status: str = Field(..., description="Task status")
    created_at: str = Field(..., description="Creation timestamp")


class ToDoListResponse(BaseModel):
    """ToDo list response model."""

    todos: List[Dict[str, Any]] = Field(..., description="List of ToDo items")
    count: int = Field(..., description="Total count")
    user_id: str = Field(..., description="User identifier")


# Dependency injection
# Keep a single service instance to persist agent memory across requests
_todo_service_singleton: Optional[ToDoService] = None


def get_todo_service(
    request: Request, settings: Settings = Depends(get_settings)
) -> ToDoService:
    """Get ToDo service instance (singleton)."""
    global _todo_service_singleton
    if _todo_service_singleton is None:
        # Get checkpointer from app state if available
        checkpointer = getattr(request.app.state, "checkpointer", None)
        _todo_service_singleton = ToDoService(settings, checkpointer=checkpointer)
    return _todo_service_singleton


# Chat endpoints
@router.post("/chat", response_model=ChatResponse)
async def chat_with_todo_agent(
    request: ChatRequest,
    user_id: str,
    todo_service: ToDoService = Depends(get_todo_service),
):
    """
    Chat with the ToDo agent.

    Args:
        request: Chat request
        user_id: User identifier
        todo_service: ToDo service instance

    Returns:
        ChatResponse: Agent response
    """
    try:
        result = await todo_service.process_message(
            message=request.message,
            user_id=user_id,
            session_id=request.session_id,
            context=request.context,
        )

        return ChatResponse(**result)

    except ValidationError as e:
        logger.warning(f"Chat request validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message
        )

    except Exception as e:
        logger.error(f"Chat request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat request failed",
        )


# ToDo management endpoints
@router.get("/todos", response_model=ToDoListResponse)
async def get_todos(
    user_id: str,
    status: Optional[str] = None,
    todo_service: ToDoService = Depends(get_todo_service),
):
    """
    Get user's ToDo items.

    Args:
        user_id: User identifier
        status: Optional status filter
        todo_service: ToDo service instance

    Returns:
        ToDoListResponse: List of ToDo items
    """
    try:
        todos = await todo_service.get_todos(user_id, status)

        return ToDoListResponse(todos=todos, count=len(todos), user_id=user_id)

    except Exception as e:
        logger.error(f"Failed to get todos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get todos",
        )


@router.post("/todos", response_model=ToDoResponse, status_code=status.HTTP_201_CREATED)
async def create_todo(
    request: ToDoRequest,
    user_id: str,
    todo_service: ToDoService = Depends(get_todo_service),
):
    """
    Create a new ToDo item.

    Args:
        request: ToDo request
        user_id: User identifier
        todo_service: ToDo service instance

    Returns:
        ToDoResponse: Created ToDo item
    """
    try:
        todo_data = request.model_dump()
        result = await todo_service.create_todo(user_id, todo_data)

        return ToDoResponse(**result)

    except ValidationError as e:
        logger.warning(f"ToDo creation validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message
        )

    except Exception as e:
        logger.error(f"Failed to create todo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create todo",
        )


@router.put("/todos/{todo_id}")
async def update_todo(
    todo_id: str,
    updates: Dict[str, Any],
    user_id: str,
    todo_service: ToDoService = Depends(get_todo_service),
):
    """
    Update a ToDo item.

    Args:
        todo_id: ToDo identifier
        updates: Update data
        user_id: User identifier
        todo_service: ToDo service instance

    Returns:
        Dict: Update result
    """
    try:
        result = await todo_service.update_todo(todo_id, updates)
        return result

    except Exception as e:
        logger.error(f"Failed to update todo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update todo",
        )


@router.delete("/todos/{todo_id}")
async def delete_todo(
    todo_id: str, user_id: str, todo_service: ToDoService = Depends(get_todo_service)
):
    """
    Delete a ToDo item.

    Args:
        todo_id: ToDo identifier
        user_id: User identifier
        todo_service: ToDo service instance

    Returns:
        Dict: Deletion result
    """
    try:
        success = await todo_service.delete_todo(todo_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="ToDo not found"
            )

        return {"message": "ToDo deleted successfully", "todo_id": todo_id}

    except Exception as e:
        logger.error(f"Failed to delete todo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete todo",
        )


# User profile endpoints
@router.get("/profile/{user_id}")
async def get_user_profile(
    user_id: str, todo_service: ToDoService = Depends(get_todo_service)
):
    """
    Get user profile.

    Args:
        user_id: User identifier
        todo_service: ToDo service instance

    Returns:
        Dict: User profile
    """
    try:
        profile = await todo_service.get_user_profile(user_id)
        return {"user_id": user_id, "profile": profile}

    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile",
        )


@router.put("/profile/{user_id}")
async def update_user_profile(
    user_id: str,
    profile_data: Dict[str, Any],
    todo_service: ToDoService = Depends(get_todo_service),
):
    """
    Update user profile.

    Args:
        user_id: User identifier
        profile_data: Profile data
        todo_service: ToDo service instance

    Returns:
        Dict: Update result
    """
    try:
        profile_id = await todo_service.update_user_profile(user_id, profile_data)
        return {"user_id": user_id, "profile_id": profile_id}

    except Exception as e:
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile",
        )


# Service information endpoints
@router.get("/stats")
async def get_service_stats(todo_service: ToDoService = Depends(get_todo_service)):
    """
    Get service statistics.

    Args:
        todo_service: ToDo service instance

    Returns:
        Dict: Service statistics
    """
    try:
        stats = await todo_service.get_service_stats()
        return stats

    except Exception as e:
        logger.error(f"Failed to get service stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get service stats",
        )
