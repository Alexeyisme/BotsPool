"""
Database query utilities for BotsPool

This module provides query builders and common database operations
for the BotsPool platform.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from .models import (
    UserModel,
    UserAuthModel,
    UserProfileModel,
    UserPreferencesModel,
    UserSessionModel,
    ChatSessionModel,
    ChatMessageModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    UsageTrackingModel,
    GraphModel,
    GraphInstanceModel,
    GraphHealthModel,
    ToDoItemModel,
    ToDoProfileModel,
    ToDoInstructionModel,
    SessionRecordModel,
)
from ..models.enums import (
    SubscriptionTier,
    GraphType,
    UserRole,
    ChatStatus,
    GraphStatus,
    FrontendType,
    AuthProvider,
    MessageType,
)
from ..errors import DatabaseQueryError


class QueryBuilder:
    """Base query builder class."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute_query(self, query) -> List[Any]:
        """Execute a query and return results."""
        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            raise DatabaseQueryError(f"Query execution failed: {e}")

    async def execute_scalar(self, query) -> Any:
        """Execute a query and return scalar result."""
        try:
            result = await self.session.execute(query)
            return result.scalar()
        except Exception as e:
            raise DatabaseQueryError(f"Scalar query execution failed: {e}")

    async def execute_one(self, query) -> Any:
        """Execute a query and return one result."""
        try:
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseQueryError(f"Single query execution failed: {e}")


class UserQueries(QueryBuilder):
    """User-related database queries."""

    async def get_user_by_id(self, user_id: UUID) -> Optional[UserModel]:
        """Get user by ID with all relationships."""
        query = (
            select(UserModel)
            .options(
                selectinload(UserModel.auth),
                selectinload(UserModel.profile),
                selectinload(UserModel.preferences),
            )
            .where(UserModel.id == user_id)
        )

        return await self.execute_one(query)

    async def get_user_by_email(self, email: str) -> Optional[UserModel]:
        """Get user by email address."""
        query = (
            select(UserModel)
            .join(UserAuthModel)
            .where(UserAuthModel.email == email)
            .options(
                selectinload(UserModel.auth),
                selectinload(UserModel.profile),
                selectinload(UserModel.preferences),
            )
        )

        return await self.execute_one(query)

    async def get_user_by_username(self, username: str) -> Optional[UserModel]:
        """Get user by username."""
        query = (
            select(UserModel)
            .join(UserProfileModel)
            .where(UserProfileModel.username == username)
            .options(
                selectinload(UserModel.auth),
                selectinload(UserModel.profile),
                selectinload(UserModel.preferences),
            )
        )

        return await self.execute_one(query)

    async def create_user(self, user_data: Dict[str, Any]) -> UserModel:
        """Create a new user."""
        user = UserModel(**user_data)
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_user(
        self, user_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[UserModel]:
        """Update user information."""
        query = update(UserModel).where(UserModel.id == user_id).values(**update_data)
        await self.session.execute(query)
        return await self.get_user_by_id(user_id)

    async def delete_user(self, user_id: UUID) -> bool:
        """Soft delete a user."""
        query = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(is_deleted=True, deleted_at=func.now())
        )
        result = await self.session.execute(query)
        return result.rowcount > 0

    async def get_users_by_role(
        self, role: UserRole, limit: int = 100
    ) -> List[UserModel]:
        """Get users by role."""
        query = (
            select(UserModel)
            .where(UserModel.role == role, UserModel.is_deleted == False)
            .limit(limit)
        )

        return await self.execute_query(query)

    async def get_users_by_subscription_tier(
        self, tier: SubscriptionTier, limit: int = 100
    ) -> List[UserModel]:
        """Get users by subscription tier."""
        query = (
            select(UserModel)
            .where(UserModel.subscription_tier == tier, UserModel.is_deleted == False)
            .limit(limit)
        )

        return await self.execute_query(query)

    async def update_user_activity(self, user_id: UUID) -> None:
        """Update user's last activity timestamp."""
        query = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(last_activity=func.now())
        )
        await self.session.execute(query)

    async def increment_user_stats(
        self, user_id: UUID, chats: int = 0, messages: int = 0
    ) -> None:
        """Increment user statistics."""
        query = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(
                total_chats=UserModel.total_chats + chats,
                total_messages=UserModel.total_messages + messages,
            )
        )
        await self.session.execute(query)


class SessionQueries(QueryBuilder):
    """Durable session record queries."""

    async def get_by_id(self, record_id: UUID) -> Optional[SessionRecordModel]:
        """Retrieve a session record by its identifier."""
        query = select(SessionRecordModel).where(SessionRecordModel.id == record_id)
        return await self.execute_one(query)

    async def get_by_frontend_reference(
        self,
        frontend_type: FrontendType,
        chat_id: str,
    ) -> Optional[SessionRecordModel]:
        """Fetch a session using the frontend/chat composite key."""
        query = select(SessionRecordModel).where(
            SessionRecordModel.frontend_type == frontend_type,
            SessionRecordModel.chat_id == chat_id,
        )
        return await self.execute_one(query)

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
    ) -> List[SessionRecordModel]:
        """List active sessions associated with a user."""
        query = (
            select(SessionRecordModel)
            .where(SessionRecordModel.user_id == user_id)
            .order_by(SessionRecordModel.last_activity_at.desc())
            .limit(limit)
        )
        return await self.execute_query(query)

    async def create_session(
        self,
        payload: Dict[str, Any],
    ) -> SessionRecordModel:
        """Persist a new session record."""
        record = SessionRecordModel(**payload)
        self.session.add(record)
        await self.session.flush()
        return record

    async def update_session(
        self,
        record_id: UUID,
        updates: Dict[str, Any],
    ) -> Optional[SessionRecordModel]:
        """Apply updates to an existing session record."""
        if not updates:
            return await self.get_by_id(record_id)

        query = (
            update(SessionRecordModel)
            .where(SessionRecordModel.id == record_id)
            .values(**updates)
            .returning(SessionRecordModel)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete_session(self, record_id: UUID) -> bool:
        """Remove a session record."""
        query = delete(SessionRecordModel).where(SessionRecordModel.id == record_id)
        result = await self.session.execute(query)
        return result.rowcount > 0

    async def purge_expired(self, now_ts: datetime) -> int:
        """Delete expired sessions."""
        query = (
            delete(SessionRecordModel)
            .where(SessionRecordModel.expires_at.isnot(None))
            .where(SessionRecordModel.expires_at < now_ts)
        )
        result = await self.session.execute(query)
        return result.rowcount or 0


class ChatQueries(QueryBuilder):
    """Chat-related database queries."""

    async def get_chat_session_by_id(
        self, session_id: str
    ) -> Optional[ChatSessionModel]:
        """Get chat session by ID."""
        query = (
            select(ChatSessionModel)
            .where(ChatSessionModel.session_id == session_id)
            .options(selectinload(ChatSessionModel.messages))
        )

        return await self.execute_one(query)

    async def get_chat_sessions_by_user(
        self, user_id: UUID, limit: int = 50
    ) -> List[ChatSessionModel]:
        """Get chat sessions for a user."""
        query = (
            select(ChatSessionModel)
            .where(ChatSessionModel.user_id == user_id)
            .order_by(ChatSessionModel.updated_at.desc())
            .limit(limit)
        )

        return await self.execute_query(query)

    async def create_chat_session(
        self, session_data: Dict[str, Any]
    ) -> ChatSessionModel:
        """Create a new chat session."""
        session = ChatSessionModel(**session_data)
        self.session.add(session)
        await self.session.flush()
        return session

    async def update_chat_session(
        self, session_id: str, update_data: Dict[str, Any]
    ) -> Optional[ChatSessionModel]:
        """Update chat session."""
        query = (
            update(ChatSessionModel)
            .where(ChatSessionModel.session_id == session_id)
            .values(**update_data)
        )

        await self.session.execute(query)
        return await self.get_chat_session_by_id(session_id)

    async def add_chat_message(self, message_data: Dict[str, Any]) -> ChatMessageModel:
        """Add a message to a chat session."""
        message = ChatMessageModel(**message_data)
        self.session.add(message)

        # Update session message count
        await self.update_session_message_count(message_data["session_id"])

        await self.session.flush()
        return message

    async def get_chat_messages(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> List[ChatMessageModel]:
        """Get chat messages for a session."""
        query = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )

        return await self.execute_query(query)

    async def update_session_message_count(self, session_id: str) -> None:
        """Update session message count."""
        # Get current count
        count_query = select(func.count(ChatMessageModel.id)).where(
            ChatMessageModel.session_id == session_id
        )
        count = await self.execute_scalar(count_query)

        # Update session
        query = (
            update(ChatSessionModel)
            .where(ChatSessionModel.session_id == session_id)
            .values(message_count=count, last_message_at=func.now())
        )
        await self.session.execute(query)

    async def end_chat_session(self, session_id: str) -> None:
        """End a chat session."""
        query = (
            update(ChatSessionModel)
            .where(ChatSessionModel.session_id == session_id)
            .values(status=ChatStatus.ENDED)
        )

        await self.session.execute(query)

    async def get_user_chat_history(
        self, user_id: UUID, limit: int = 100
    ) -> List[ChatMessageModel]:
        """Get user's chat history."""
        query = (
            select(ChatMessageModel)
            .where(ChatMessageModel.user_id == user_id)
            .order_by(ChatMessageModel.timestamp.desc())
            .limit(limit)
        )

        return await self.execute_query(query)


class SubscriptionQueries(QueryBuilder):
    """Subscription-related database queries."""

    async def get_subscription_by_user_id(
        self, user_id: UUID
    ) -> Optional[SubscriptionModel]:
        """Get user's subscription."""
        query = (
            select(SubscriptionModel)
            .where(
                SubscriptionModel.user_id == user_id,
                SubscriptionModel.is_active == True,
            )
            .options(selectinload(SubscriptionModel.plan))
        )

        return await self.execute_one(query)

    async def get_subscription_plan_by_tier(
        self, tier: SubscriptionTier
    ) -> Optional[SubscriptionPlanModel]:
        """Get subscription plan by tier."""
        query = select(SubscriptionPlanModel).where(
            SubscriptionPlanModel.tier == tier, SubscriptionPlanModel.is_active == True
        )

        return await self.execute_one(query)

    async def create_subscription(
        self, subscription_data: Dict[str, Any]
    ) -> SubscriptionModel:
        """Create a new subscription."""
        subscription = SubscriptionModel(**subscription_data)
        self.session.add(subscription)
        await self.session.flush()
        return subscription

    async def update_subscription(
        self, subscription_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[SubscriptionModel]:
        """Update subscription."""
        query = (
            update(SubscriptionModel)
            .where(SubscriptionModel.id == subscription_id)
            .values(**update_data)
        )

        await self.session.execute(query)
        return await self.get_subscription_by_id(subscription_id)

    async def get_subscription_by_id(
        self, subscription_id: UUID
    ) -> Optional[SubscriptionModel]:
        """Get subscription by ID."""
        query = (
            select(SubscriptionModel)
            .where(SubscriptionModel.id == subscription_id)
            .options(
                selectinload(SubscriptionModel.plan),
                selectinload(SubscriptionModel.usage),
            )
        )

        return await self.execute_one(query)

    async def get_usage_tracking_by_user_id(
        self, user_id: UUID
    ) -> Optional[UsageTrackingModel]:
        """Get usage tracking for a user."""
        query = select(UsageTrackingModel).where(UsageTrackingModel.user_id == user_id)

        return await self.execute_one(query)

    async def update_usage_tracking(
        self, user_id: UUID, usage_data: Dict[str, Any]
    ) -> Optional[UsageTrackingModel]:
        """Update usage tracking."""
        query = (
            update(UsageTrackingModel)
            .where(UsageTrackingModel.user_id == user_id)
            .values(**usage_data)
        )

        await self.session.execute(query)
        return await self.get_usage_tracking_by_user_id(user_id)

    async def increment_usage(
        self, user_id: UUID, graph_type: str, tokens_used: int = 0
    ) -> None:
        """Increment usage counters."""
        # Update usage tracking
        query = (
            update(UsageTrackingModel)
            .where(UsageTrackingModel.user_id == user_id)
            .values(
                requests_current_minute=UsageTrackingModel.requests_current_minute + 1,
                requests_current_hour=UsageTrackingModel.requests_current_hour + 1,
                requests_current_day=UsageTrackingModel.requests_current_day + 1,
                requests_current_month=UsageTrackingModel.requests_current_month + 1,
                tokens_current_day=UsageTrackingModel.tokens_current_day + tokens_used,
                tokens_current_month=UsageTrackingModel.tokens_current_month
                + tokens_used,
                last_request_at=func.now(),
            )
        )

        await self.session.execute(query)


class GraphQueries(QueryBuilder):
    """Graph-related database queries."""

    async def get_graph_by_type(self, graph_type: GraphType) -> Optional[GraphModel]:
        """Get graph by graph type."""
        query = (
            select(GraphModel)
            .where(GraphModel.graph_type == graph_type)
            .options(selectinload(GraphModel.instances))
        )

        return await self.execute_one(query)

    async def get_all_graphs(self) -> List[GraphModel]:
        """Get all available graphs."""
        query = (
            select(GraphModel)
            .where(GraphModel.is_available == True)
            .options(selectinload(GraphModel.instances))
        )

        return await self.execute_query(query)

    async def get_graph_instance_by_id(
        self, instance_id: str
    ) -> Optional[GraphInstanceModel]:
        """Get graph instance by ID."""
        query = (
            select(GraphInstanceModel)
            .where(GraphInstanceModel.instance_id == instance_id)
            .options(
                selectinload(GraphInstanceModel.graph),
                selectinload(GraphInstanceModel.health),
            )
        )

        return await self.execute_one(query)

    async def get_available_graph_instances(
        self, graph_type: GraphType
    ) -> List[GraphInstanceModel]:
        """Get available graph instances for a graph type."""
        query = (
            select(GraphInstanceModel)
            .join(GraphModel)
            .where(
                GraphModel.graph_type == graph_type,
                GraphInstanceModel.status == GraphStatus.HEALTHY,
            )
            .options(selectinload(GraphInstanceModel.health))
        )

        return await self.execute_query(query)

    async def update_graph_instance_status(
        self, instance_id: str, status: GraphStatus
    ) -> None:
        """Update graph instance status."""
        query = (
            update(GraphInstanceModel)
            .where(GraphInstanceModel.instance_id == instance_id)
            .values(status=status)
        )

        await self.session.execute(query)

    async def update_graph_instance_load(
        self, instance_id: str, load_delta: int
    ) -> None:
        """Update graph instance load."""
        query = (
            update(GraphInstanceModel)
            .where(GraphInstanceModel.instance_id == instance_id)
            .values(current_load=GraphInstanceModel.current_load + load_delta)
        )

        await self.session.execute(query)

    async def update_graph_health(
        self, instance_id: str, health_data: Dict[str, Any]
    ) -> None:
        """Update graph health metrics."""
        query = (
            update(GraphHealthModel)
            .where(GraphHealthModel.instance_id == instance_id)
            .values(**health_data)
        )

        await self.session.execute(query)

    async def create_graph_instance(
        self, instance_data: Dict[str, Any]
    ) -> GraphInstanceModel:
        """Create a new graph instance."""
        instance = GraphInstanceModel(**instance_data)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def remove_graph_instance(self, instance_id: str) -> bool:
        """Remove a graph instance."""
        query = delete(GraphInstanceModel).where(
            GraphInstanceModel.instance_id == instance_id
        )

        result = await self.session.execute(query)
        return result.rowcount > 0


class ToDoQueries(QueryBuilder):
    """Queries for ToDo persistence tables."""

    # Profiles
    async def upsert_profile(
        self, user_id: UUID, profile: Dict[str, Any]
    ) -> ToDoProfileModel:
        existing = await self.execute_one(
            select(ToDoProfileModel).where(ToDoProfileModel.user_id == user_id)
        )

        if existing:
            existing.profile = profile
            await self.session.flush()
            return existing

        record = ToDoProfileModel(user_id=user_id, profile=profile)
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_profile(self, user_id: UUID) -> Optional[ToDoProfileModel]:
        return await self.execute_one(
            select(ToDoProfileModel).where(ToDoProfileModel.user_id == user_id)
        )

    # Instructions
    async def upsert_instructions(
        self, user_id: UUID, instructions: str, extra: Optional[Dict[str, Any]] = None
    ) -> ToDoInstructionModel:
        existing = await self.execute_one(
            select(ToDoInstructionModel).where(ToDoInstructionModel.user_id == user_id)
        )

        if existing:
            existing.instructions = instructions
            existing.extra = extra or existing.extra
            await self.session.flush()
            return existing

        record = ToDoInstructionModel(
            user_id=user_id, instructions=instructions, extra=extra
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_instructions(self, user_id: UUID) -> Optional[ToDoInstructionModel]:
        return await self.execute_one(
            select(ToDoInstructionModel).where(ToDoInstructionModel.user_id == user_id)
        )

    # ToDo items
    async def create_todo(
        self, user_id: UUID, payload: Dict[str, Any]
    ) -> ToDoItemModel:
        record = ToDoItemModel(user_id=user_id, **payload)
        self.session.add(record)
        await self.session.flush()
        return record

    async def list_todos(
        self, user_id: UUID, status: Optional[str] = None
    ) -> List[ToDoItemModel]:
        query = (
            select(ToDoItemModel)
            .where(ToDoItemModel.user_id == user_id)
            .order_by(ToDoItemModel.created_at.asc())
        )
        if status:
            query = query.where(ToDoItemModel.status == status)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_todo(self, todo_id: UUID) -> Optional[ToDoItemModel]:
        return await self.execute_one(
            select(ToDoItemModel).where(ToDoItemModel.id == todo_id)
        )

    async def update_todo(
        self, todo_id: UUID, updates: Dict[str, Any]
    ) -> Optional[ToDoItemModel]:
        if not updates:
            return await self.get_todo(todo_id)

        await self.session.execute(
            update(ToDoItemModel).where(ToDoItemModel.id == todo_id).values(**updates)
        )
        return await self.get_todo(todo_id)

    async def delete_todo(self, todo_id: UUID) -> bool:
        result = await self.session.execute(
            delete(ToDoItemModel).where(ToDoItemModel.id == todo_id)
        )
        return result.rowcount > 0
