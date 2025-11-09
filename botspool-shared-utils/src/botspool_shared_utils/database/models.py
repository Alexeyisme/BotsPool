"""
SQLAlchemy ORM models for BotsPool

This module contains SQLAlchemy ORM models that correspond to the Pydantic models
defined in the models module.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

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

# Create base class for all models
Base = declarative_base()


class TimestampMixin:
    """Mixin for timestamp fields."""

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)


class UserAuthModel(Base, TimestampMixin):
    """User authentication information."""

    __tablename__ = "user_auth"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )

    # Authentication fields
    provider = Column(Enum(AuthProvider), nullable=False)
    provider_id = Column(String(255), nullable=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)

    # MFA fields
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255), nullable=True)

    # Login tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("UserModel", back_populates="auth")

    # Indexes
    __table_args__ = (
        Index("idx_user_auth_email", "email"),
        Index("idx_user_auth_provider", "provider"),
    )


class UserProfileModel(Base, TimestampMixin):
    """User profile information."""

    __tablename__ = "user_profiles"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )

    # Profile fields
    username = Column(String(50), nullable=False, unique=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    display_name = Column(String(150), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)

    # Preferences
    timezone = Column(String(50), default="UTC", nullable=False)
    language = Column(String(5), default="en", nullable=False)
    country = Column(String(2), nullable=True)

    # Relationships
    user = relationship("UserModel", back_populates="profile")

    # Indexes
    __table_args__ = (
        Index("idx_user_profile_username", "username"),
        Index("idx_user_profile_display_name", "display_name"),
    )


class UserPreferencesModel(Base, TimestampMixin):
    """User preferences and settings."""

    __tablename__ = "user_preferences"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )

    # Notification preferences
    email_notifications = Column(Boolean, default=True, nullable=False)
    push_notifications = Column(Boolean, default=True, nullable=False)
    sms_notifications = Column(Boolean, default=False, nullable=False)

    # Chat preferences
    default_graph = Column(String(50), nullable=True)
    auto_route = Column(Boolean, default=True, nullable=False)
    chat_history_retention = Column(Integer, default=30, nullable=False)

    # Privacy preferences
    data_sharing = Column(Boolean, default=False, nullable=False)
    profile_visibility = Column(String(20), default="private", nullable=False)

    # UI preferences
    theme = Column(String(20), default="light", nullable=False)
    compact_mode = Column(Boolean, default=False, nullable=False)

    # Advanced preferences
    debug_mode = Column(Boolean, default=False, nullable=False)
    beta_features = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("UserModel", back_populates="preferences")


class UserModel(Base, TimestampMixin, SoftDeleteMixin):
    """Main user model."""

    __tablename__ = "users"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    # System information
    role = Column(Enum(UserRole), default=UserRole.FREE_USER, nullable=False)
    subscription_tier = Column(
        Enum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    is_suspended = Column(Boolean, default=False, nullable=False)

    # Timestamps
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)

    # Statistics
    total_chats = Column(Integer, default=0, nullable=False)
    total_messages = Column(Integer, default=0, nullable=False)

    # Relationships
    auth = relationship("UserAuthModel", back_populates="user", uselist=False)
    profile = relationship("UserProfileModel", back_populates="user", uselist=False)
    preferences = relationship(
        "UserPreferencesModel", back_populates="user", uselist=False
    )
    sessions = relationship("UserSessionModel", back_populates="user")
    chat_sessions = relationship("ChatSessionModel", back_populates="user")
    subscriptions = relationship("SubscriptionModel", back_populates="user")

    # Indexes
    __table_args__ = (
        Index("idx_users_role", "role"),
        Index("idx_users_subscription_tier", "subscription_tier"),
        Index("idx_users_is_active", "is_active"),
        Index("idx_users_last_activity", "last_activity"),
    )


class UserSessionModel(Base, TimestampMixin):
    """User session tracking."""

    __tablename__ = "user_sessions"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Session information
    session_id = Column(String(255), nullable=False, unique=True, index=True)
    frontend_type = Column(Enum(FrontendType), nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)

    # Session state
    last_activity = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("UserModel", back_populates="sessions")

    # Indexes
    __table_args__ = (
        Index("idx_user_sessions_user_id", "user_id"),
        Index("idx_user_sessions_session_id", "session_id"),
        Index("idx_user_sessions_expires_at", "expires_at"),
        Index("idx_user_sessions_is_active", "is_active"),
    )


class SessionRecordModel(Base, TimestampMixin):
    """Durable session state for frontend interactions (e.g., Telegram)."""

    __tablename__ = "session_records"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    frontend_type = Column(Enum(FrontendType), nullable=False)
    chat_id = Column(String(128), nullable=False)
    user_id = Column(PostgresUUID(as_uuid=True), nullable=True)
    current_agent = Column(String(100), nullable=True)
    locale = Column(String(10), nullable=True)
    state_blob = Column(JSON, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "frontend_type", "chat_id", name="uq_session_records_frontend_chat"
        ),
        Index("idx_session_records_user_id", "user_id"),
        Index("idx_session_records_expires_at", "expires_at"),
        Index("idx_session_records_last_activity_at", "last_activity_at"),
    )


class ChatSessionModel(Base, TimestampMixin):
    """Chat session model."""

    __tablename__ = "chat_sessions"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Session information
    session_id = Column(String(255), nullable=False, unique=True, index=True)
    frontend_type = Column(Enum(FrontendType), nullable=False)
    status = Column(Enum(ChatStatus), default=ChatStatus.ACTIVE, nullable=False)

    # Session metadata
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)

    # Context and state
    context = Column(JSON, nullable=True)
    current_graph = Column(Enum(GraphType), nullable=True)

    # Statistics
    message_count = Column(Integer, default=0, nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)

    # Frontend-specific data
    frontend_data = Column(JSON, nullable=True)

    # Relationships
    user = relationship("UserModel", back_populates="chat_sessions")
    messages = relationship("ChatMessageModel", back_populates="session")

    # Indexes
    __table_args__ = (
        Index("idx_chat_sessions_user_id", "user_id"),
        Index("idx_chat_sessions_session_id", "session_id"),
        Index("idx_chat_sessions_status", "status"),
        Index("idx_chat_sessions_current_graph", "current_graph"),
        Index("idx_chat_sessions_last_message_at", "last_message_at"),
    )


class ChatMessageModel(Base, TimestampMixin):
    """Chat message model."""

    __tablename__ = "chat_messages"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False
    )
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Message information
    message_type = Column(Enum(MessageType), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Graph information
    graph_type = Column(Enum(GraphType), nullable=True)

    # Metadata
    message_metadata = Column(JSON, nullable=True)

    # Relationships
    session = relationship("ChatSessionModel", back_populates="messages")
    user = relationship("UserModel")

    # Indexes
    __table_args__ = (
        Index("idx_chat_messages_session_id", "session_id"),
        Index("idx_chat_messages_user_id", "user_id"),
        Index("idx_chat_messages_message_type", "message_type"),
        Index("idx_chat_messages_graph_type", "graph_type"),
        Index("idx_chat_messages_timestamp", "timestamp"),
    )


class SubscriptionPlanModel(Base, TimestampMixin):
    """Subscription plan model."""

    __tablename__ = "subscription_plans"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Plan information
    tier = Column(Enum(SubscriptionTier), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Pricing
    price_monthly = Column(Integer, nullable=False)  # Price in cents
    price_yearly = Column(Integer, nullable=False)  # Price in cents
    currency = Column(String(3), default="USD", nullable=False)

    # Limits (stored as JSON for flexibility)
    limits = Column(JSON, nullable=False)

    # Features
    features = Column(JSON, nullable=True)

    # Billing
    billing_cycle = Column(String(20), default="monthly", nullable=False)
    trial_days = Column(Integer, default=0, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_popular = Column(Boolean, default=False, nullable=False)

    # Relationships
    subscriptions = relationship("SubscriptionModel", back_populates="plan")

    # Indexes
    __table_args__ = (
        Index("idx_subscription_plans_tier", "tier"),
        Index("idx_subscription_plans_is_active", "is_active"),
    )


class UsageTrackingModel(Base, TimestampMixin):
    """Usage tracking model."""

    __tablename__ = "usage_tracking"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )
    subscription_tier = Column(Enum(SubscriptionTier), nullable=False)

    # Current usage (rolling windows)
    requests_current_minute = Column(Integer, default=0, nullable=False)
    requests_current_hour = Column(Integer, default=0, nullable=False)
    requests_current_day = Column(Integer, default=0, nullable=False)
    requests_current_month = Column(Integer, default=0, nullable=False)

    # Token usage
    tokens_current_day = Column(Integer, default=0, nullable=False)
    tokens_current_month = Column(Integer, default=0, nullable=False)

    # Session tracking
    active_sessions = Column(Integer, default=0, nullable=False)

    # Usage by graph
    usage_by_graph = Column(JSON, nullable=True)

    # Timestamps
    last_request_at = Column(DateTime(timezone=True), nullable=True)
    last_reset_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user = relationship("UserModel")

    # Indexes
    __table_args__ = (
        Index("idx_usage_tracking_user_id", "user_id"),
        Index("idx_usage_tracking_subscription_tier", "subscription_tier"),
        Index("idx_usage_tracking_last_reset_at", "last_reset_at"),
    )


class SubscriptionModel(Base, TimestampMixin):
    """User subscription model."""

    __tablename__ = "subscriptions"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plan_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False
    )

    # Subscription status
    status = Column(String(20), default="active", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Billing information
    billing_cycle = Column(String(20), default="monthly", nullable=False)
    next_billing_date = Column(DateTime(timezone=True), nullable=False)
    last_billing_date = Column(DateTime(timezone=True), nullable=True)

    # Trial information
    is_trial = Column(Boolean, default=False, nullable=False)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)

    # Payment information
    payment_method_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)

    # Cancellation
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(String(255), nullable=True)

    # Relationships
    user = relationship("UserModel", back_populates="subscriptions")
    plan = relationship("SubscriptionPlanModel", back_populates="subscriptions")
    # Note: usage relationship removed as it's not properly linked via foreign key

    # Indexes
    __table_args__ = (
        Index("idx_subscriptions_user_id", "user_id"),
        Index("idx_subscriptions_plan_id", "plan_id"),
        Index("idx_subscriptions_status", "status"),
        Index("idx_subscriptions_is_active", "is_active"),
        Index("idx_subscriptions_next_billing_date", "next_billing_date"),
        UniqueConstraint("user_id", "plan_id", name="uq_user_plan"),
    )


class GraphModel(Base, TimestampMixin):
    """Graph model."""

    __tablename__ = "graphs"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Graph information
    graph_type = Column(Enum(GraphType), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Graph metadata
    version = Column(String(20), nullable=False)
    author = Column(String(100), nullable=False)
    tags = Column(JSON, nullable=True)

    # Status and availability
    status = Column(Enum(GraphStatus), default=GraphStatus.OFFLINE, nullable=False)
    is_available = Column(Boolean, default=False, nullable=False)

    # Configuration
    default_config = Column(JSON, nullable=False)

    # Statistics
    total_requests = Column(Integer, default=0, nullable=False)
    total_users = Column(Integer, default=0, nullable=False)

    # Timestamps
    last_deployment = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    instances = relationship("GraphInstanceModel", back_populates="graph")

    # Indexes
    __table_args__ = (
        Index("idx_graphs_graph_type", "graph_type"),
        Index("idx_graphs_status", "status"),
        Index("idx_graphs_is_available", "is_available"),
    )


class GraphHealthModel(Base, TimestampMixin):
    """Graph health status model."""

    __tablename__ = "graph_health"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    instance_id = Column(String(255), nullable=False, unique=True, index=True)

    # Health status
    status = Column(Enum(GraphStatus), nullable=False)

    # Performance metrics
    response_time_avg = Column(Integer, default=0, nullable=False)  # Milliseconds
    response_time_p95 = Column(Integer, default=0, nullable=False)  # Milliseconds
    requests_per_minute = Column(Integer, default=0, nullable=False)
    error_rate = Column(Integer, default=0, nullable=False)  # Percentage (0-100)

    # Resource usage
    cpu_usage = Column(Integer, default=0, nullable=False)  # Percentage (0-100)
    memory_usage = Column(Integer, default=0, nullable=False)  # Percentage (0-100)

    # Request statistics
    total_requests = Column(Integer, default=0, nullable=False)
    successful_requests = Column(Integer, default=0, nullable=False)
    failed_requests = Column(Integer, default=0, nullable=False)

    # Timestamps
    last_health_check = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_request_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_graph_health_instance_id", "instance_id"),
        Index("idx_graph_health_status", "status"),
        Index("idx_graph_health_last_health_check", "last_health_check"),
    )


class GraphInstanceModel(Base, TimestampMixin):
    """Graph instance model."""

    __tablename__ = "graph_instances"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    graph_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("graphs.id"), nullable=False
    )

    # Instance information
    instance_id = Column(String(255), nullable=False, unique=True, index=True)
    version = Column(String(20), nullable=False)
    endpoint = Column(String(500), nullable=False)
    region = Column(String(50), default="us-east-1", nullable=False)

    # Status and health
    status = Column(Enum(GraphStatus), default=GraphStatus.OFFLINE, nullable=False)
    health_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("graph_health.id"), nullable=True
    )

    # Configuration
    config = Column(JSON, nullable=False)

    # Capacity and load
    max_capacity = Column(Integer, default=100, nullable=False)
    current_load = Column(Integer, default=0, nullable=False)

    # Deployment information
    deployment_id = Column(String(255), nullable=True)
    container_id = Column(String(255), nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    graph = relationship("GraphModel", back_populates="instances")
    health = relationship("GraphHealthModel")

    # Indexes
    __table_args__ = (
        Index("idx_graph_instances_graph_id", "graph_id"),
        Index("idx_graph_instances_instance_id", "instance_id"),
        Index("idx_graph_instances_status", "status"),
        Index("idx_graph_instances_region", "region"),
        Index("idx_graph_instances_last_heartbeat", "last_heartbeat"),
    )


class ToDoItemModel(Base, TimestampMixin):
    """Persisted ToDo items for LangGraph memory."""

    __tablename__ = "todo_items"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)

    task = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="not_started")
    priority = Column(String(20), nullable=True)
    category = Column(String(50), nullable=True)
    time_to_complete = Column(Integer, nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    solutions = Column(JSON, nullable=False, default=list)
    extra = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_todo_items_user_status", "user_id", "status"),
        Index("idx_todo_items_deadline", "deadline"),
    )


class ToDoProfileModel(Base, TimestampMixin):
    """Stored structured profile data extracted by the ToDo agent."""

    __tablename__ = "todo_profiles"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), nullable=False, unique=True)
    profile = Column(JSON, nullable=False)

    __table_args__ = (Index("idx_todo_profiles_user_id", "user_id"),)


class ToDoInstructionModel(Base, TimestampMixin):
    """User-specific instructions captured by the ToDo agent."""

    __tablename__ = "todo_instructions"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), nullable=False, unique=True)
    instructions = Column(Text, nullable=False)
    extra = Column(JSON, nullable=True)

    __table_args__ = (Index("idx_todo_instructions_user_id", "user_id"),)
