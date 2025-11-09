"""
ToDo Service for BotsPool ToDo Graph

Business logic for task management operations.
"""

import logging
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime

from botspool_shared_utils.errors import ValidationError, ErrorCode
from ..agents.todo_agent import ToDoAgent
from ..memory.todo_memory import ToDoMemory
from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


class ToDoService:
    """Service for ToDo operations."""

    def __init__(self, settings: Settings, checkpointer=None):
        self.settings = settings
        self.agent = ToDoAgent(settings, checkpointer=checkpointer)
        self.memory = ToDoMemory(settings)
        self.logger = logging.getLogger(__name__)

    async def process_message(
        self,
        message: str,
        user_id: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message and return response.

        Args:
            message: User message
            user_id: User identifier
            session_id: Session identifier
            context: Additional context

        Returns:
            Dict containing response and metadata
        """
        try:
            # Validate input
            if not message or len(message.strip()) == 0:
                raise ValidationError(
                    message="Message cannot be empty",
                    error_code=ErrorCode.VALIDATION_INVALID_INPUT_301,
                    details={"field": "message"},
                )

            if len(message) > 10000:
                raise ValidationError(
                    message="Message too long",
                    error_code=ErrorCode.VALIDATION_INVALID_INPUT_301,
                    details={
                        "field": "message",
                        "max_length": 10000,
                        "actual_length": len(message),
                    },
                )

            # Process with agent
            # session_id is used to construct thread_id for persistence
            agent_config = {
                "session_id": session_id,
                "todo_category": context.get("todo_category", "general")
                if context
                else "general",
                "task_maistro_role": context.get(
                    "task_maistro_role",
                    "You are a helpful task management assistant. You help create, organize, and manage the user's ToDo list.",
                )
                if context
                else "You are a helpful task management assistant. You help create, organize, and manage the user's ToDo list.",
            }
            response = await self.agent.process_message(
                message=message, user_id=user_id, config=agent_config
            )

            # Get memory stats
            memory_stats = await self.memory.get_memory_stats(user_id)

            return {
                "response": response,
                "user_id": user_id,
                "session_id": session_id
                or f"session_{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "graph_type": "todo",
                "memory_stats": memory_stats,
                "metadata": {
                    "processing_time": 0.5,  # Mock processing time
                    "model": self.settings.openai_model,
                    "version": self.settings.app_version,
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to process message: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def get_todos(
        self, user_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user's ToDo items.

        Args:
            user_id: User identifier
            status: Optional status filter

        Returns:
            List of ToDo items
        """
        try:
            todos = await self.memory.get_todos(user_id, status)
            return todos

        except Exception as e:
            self.logger.error(f"Failed to get todos: {e}")
            raise

    async def create_todo(
        self, user_id: str, todo_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new ToDo item.

        Args:
            user_id: User identifier
            todo_data: ToDo data

        Returns:
            Created ToDo item
        """
        try:
            # Validate ToDo data
            if "task" not in todo_data:
                raise ValidationError(
                    message="Task description is required",
                    error_code=ErrorCode.VALIDATION_INVALID_INPUT_301,
                    details={"field": "task"},
                )

            # Save to memory
            todo_id = await self.memory.save_todo(user_id, todo_data)

            return {
                "todo_id": todo_id,
                "user_id": user_id,
                "task": todo_data["task"],
                "status": todo_data.get("status", "not started"),
                "created_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to create todo: {e}")
            raise

    async def update_todo(
        self, todo_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a ToDo item.

        Args:
            todo_id: ToDo identifier
            updates: Update data

        Returns:
            Updated ToDo item
        """
        try:
            success = await self.memory.update_todo(todo_id, updates)

            if not success:
                raise Exception("Failed to update todo")

            return {
                "todo_id": todo_id,
                "updated_at": datetime.now().isoformat(),
                "updates": updates,
            }

        except Exception as e:
            self.logger.error(f"Failed to update todo: {e}")
            raise

    async def delete_todo(self, todo_id: str) -> bool:
        """
        Delete a ToDo item.

        Args:
            todo_id: ToDo identifier

        Returns:
            True if deleted successfully
        """
        try:
            success = await self.memory.delete_todo(todo_id)
            return success

        except Exception as e:
            self.logger.error(f"Failed to delete todo: {e}")
            raise

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile.

        Args:
            user_id: User identifier

        Returns:
            User profile data
        """
        try:
            profile = await self.memory.get_profile(user_id)
            return profile

        except Exception as e:
            self.logger.error(f"Failed to get user profile: {e}")
            raise

    async def update_user_profile(
        self, user_id: str, profile_data: Dict[str, Any]
    ) -> str:
        """
        Update user profile.

        Args:
            user_id: User identifier
            profile_data: Profile data

        Returns:
            Profile ID
        """
        try:
            profile_id = await self.memory.save_profile(user_id, profile_data)
            return profile_id

        except Exception as e:
            self.logger.error(f"Failed to update user profile: {e}")
            raise

    async def get_service_stats(self) -> Dict[str, Any]:
        """
        Get service statistics.

        Returns:
            Service statistics
        """
        try:
            return {
                "service_name": "BotsPool ToDo Graph",
                "version": self.settings.app_version,
                "graph_type": self.settings.graph_type,
                "model": self.settings.openai_model,
                "uptime": "running",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get service stats: {e}")
            raise
