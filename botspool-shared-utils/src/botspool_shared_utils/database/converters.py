"""
Model converters between Pydantic and SQLAlchemy models.

This module provides utilities to convert between Pydantic models (used for validation
and serialization) and SQLAlchemy ORM models (used for database operations).
"""

from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from ..models.user import User, UserAuth, UserProfile, UserPreferences, UserSession
from ..models.chat import ChatSession, ChatMessage, ChatContext
from ..models.subscription import (
    Subscription,
    SubscriptionPlan,
    UsageTracking,
    UsageLimit,
)
from ..models.graph import Graph, GraphConfig, GraphInstance
from ..models.enums import (
    UserRole,
    SubscriptionTier,
    GraphType,
    ChatStatus,
    GraphStatus,
    FrontendType,
    AuthProvider,
    MessageType,
)
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
)


def pydantic_to_sqlalchemy_user(pydantic_user: User) -> UserModel:
    """Convert Pydantic User to SQLAlchemy UserModel."""
    sqlalchemy_user = UserModel(
        id=pydantic_user.id or uuid4(),
        role=pydantic_user.role,
        subscription_tier=pydantic_user.subscription_tier,
        is_active=pydantic_user.is_active,
        is_suspended=pydantic_user.is_suspended,
        email_verified_at=pydantic_user.email_verified_at,
        last_activity=pydantic_user.last_activity,
        total_chats=pydantic_user.total_chats,
        total_messages=pydantic_user.total_messages,
        created_at=pydantic_user.created_at,
        updated_at=pydantic_user.updated_at,
        deleted_at=pydantic_user.deleted_at,
        is_deleted=pydantic_user.is_deleted,
        metadata=pydantic_user.metadata,
    )

    # Add auth if present
    if pydantic_user.auth:
        sqlalchemy_user.auth = pydantic_to_sqlalchemy_user_auth(
            pydantic_user.auth, sqlalchemy_user.id
        )

    # Add profile if present
    if pydantic_user.profile:
        sqlalchemy_user.profile = pydantic_to_sqlalchemy_user_profile(
            pydantic_user.profile, sqlalchemy_user.id
        )

    # Add preferences if present
    if pydantic_user.preferences:
        sqlalchemy_user.preferences = pydantic_to_sqlalchemy_user_preferences(
            pydantic_user.preferences, sqlalchemy_user.id
        )

    return sqlalchemy_user


def pydantic_to_sqlalchemy_user_auth(
    pydantic_auth: UserAuth, user_id: UUID
) -> UserAuthModel:
    """Convert Pydantic UserAuth to SQLAlchemy UserAuthModel."""
    return UserAuthModel(
        id=uuid4(),
        user_id=user_id,
        provider=pydantic_auth.provider,
        provider_id=pydantic_auth.provider_id,
        email=pydantic_auth.email,
        password_hash=pydantic_auth.password_hash,
        is_verified=pydantic_auth.is_verified,
        mfa_enabled=pydantic_auth.mfa_enabled,
        mfa_secret=pydantic_auth.mfa_secret,
        last_login=pydantic_auth.last_login,
        failed_login_attempts=pydantic_auth.failed_login_attempts,
        locked_until=pydantic_auth.locked_until,
        created_at=pydantic_auth.created_at,
        updated_at=pydantic_auth.updated_at,
    )


def pydantic_to_sqlalchemy_user_profile(
    pydantic_profile: UserProfile, user_id: UUID
) -> UserProfileModel:
    """Convert Pydantic UserProfile to SQLAlchemy UserProfileModel."""
    return UserProfileModel(
        id=uuid4(),
        user_id=user_id,
        username=pydantic_profile.username,
        first_name=pydantic_profile.first_name,
        last_name=pydantic_profile.last_name,
        display_name=pydantic_profile.display_name,
        avatar_url=pydantic_profile.avatar_url,
        bio=pydantic_profile.bio,
        timezone=pydantic_profile.timezone,
        language=pydantic_profile.language,
        country=pydantic_profile.country,
        created_at=pydantic_profile.created_at,
        updated_at=pydantic_profile.updated_at,
    )


def pydantic_to_sqlalchemy_user_preferences(
    pydantic_preferences: UserPreferences, user_id: UUID
) -> UserPreferencesModel:
    """Convert Pydantic UserPreferences to SQLAlchemy UserPreferencesModel."""
    return UserPreferencesModel(
        id=uuid4(),
        user_id=user_id,
        email_notifications=pydantic_preferences.email_notifications,
        push_notifications=pydantic_preferences.push_notifications,
        sms_notifications=pydantic_preferences.sms_notifications,
        default_graph=pydantic_preferences.default_graph,
        auto_route=pydantic_preferences.auto_route,
        chat_history_retention=pydantic_preferences.chat_history_retention,
        data_sharing=pydantic_preferences.data_sharing,
        profile_visibility=pydantic_preferences.profile_visibility,
        theme=pydantic_preferences.theme,
        compact_mode=pydantic_preferences.compact_mode,
        debug_mode=pydantic_preferences.debug_mode,
        beta_features=pydantic_preferences.beta_features,
        created_at=pydantic_preferences.created_at,
        updated_at=pydantic_preferences.updated_at,
    )


def pydantic_to_sqlalchemy_chat_session(pydantic_chat: ChatSession) -> ChatSessionModel:
    """Convert Pydantic ChatSession to SQLAlchemy ChatSessionModel."""
    return ChatSessionModel(
        id=pydantic_chat.id or uuid4(),
        user_id=pydantic_chat.user_id,
        session_id=pydantic_chat.session_id,
        frontend_type=pydantic_chat.frontend_type,
        status=pydantic_chat.status,
        title=pydantic_chat.title,
        description=pydantic_chat.description,
        context=pydantic_chat.context.dict() if pydantic_chat.context else None,
        current_graph=pydantic_chat.current_graph,
        message_count=pydantic_chat.message_count,
        last_message_at=pydantic_chat.last_message_at,
        frontend_data=pydantic_chat.frontend_data,
        created_at=pydantic_chat.created_at,
        updated_at=pydantic_chat.updated_at,
    )


def pydantic_to_sqlalchemy_chat_message(
    pydantic_message: ChatMessage,
) -> ChatMessageModel:
    """Convert Pydantic ChatMessage to SQLAlchemy ChatMessageModel."""
    return ChatMessageModel(
        id=pydantic_message.id or uuid4(),
        session_id=pydantic_message.session_id,
        user_id=pydantic_message.user_id,
        message_type=pydantic_message.message_type,
        content=pydantic_message.content,
        timestamp=pydantic_message.timestamp,
        graph_type=pydantic_message.graph_type,
        message_metadata=pydantic_message.metadata,
        created_at=pydantic_message.created_at,
        updated_at=pydantic_message.updated_at,
    )


def pydantic_to_sqlalchemy_subscription(
    pydantic_subscription: Subscription,
) -> SubscriptionModel:
    """Convert Pydantic Subscription to SQLAlchemy SubscriptionModel."""
    return SubscriptionModel(
        id=pydantic_subscription.id or uuid4(),
        user_id=pydantic_subscription.user_id,
        plan_id=pydantic_subscription.plan.id
        if pydantic_subscription.plan
        else uuid4(),
        status=pydantic_subscription.status,
        is_active=pydantic_subscription.is_active,
        billing_cycle=pydantic_subscription.billing_cycle,
        next_billing_date=pydantic_subscription.next_billing_date,
        last_billing_date=pydantic_subscription.last_billing_date,
        is_trial=pydantic_subscription.is_trial,
        trial_ends_at=pydantic_subscription.trial_ends_at,
        payment_method_id=pydantic_subscription.payment_method_id,
        stripe_subscription_id=pydantic_subscription.stripe_subscription_id,
        cancelled_at=pydantic_subscription.cancelled_at,
        cancellation_reason=pydantic_subscription.cancellation_reason,
        created_at=pydantic_subscription.created_at,
        updated_at=pydantic_subscription.updated_at,
    )


def pydantic_to_sqlalchemy_graph(pydantic_graph: Graph) -> GraphModel:
    """Convert Pydantic Graph to SQLAlchemy GraphModel."""
    return GraphModel(
        id=pydantic_graph.id or uuid4(),
        graph_type=pydantic_graph.graph_type,
        name=pydantic_graph.name,
        description=pydantic_graph.description,
        version=pydantic_graph.version,
        author=pydantic_graph.author,
        tags=pydantic_graph.tags,
        status=pydantic_graph.status,
        is_available=pydantic_graph.is_available,
        default_config=pydantic_graph.default_config.dict()
        if pydantic_graph.default_config
        else {},
        total_requests=pydantic_graph.total_requests,
        total_users=pydantic_graph.total_users,
        last_deployment=pydantic_graph.last_deployment,
        created_at=pydantic_graph.created_at,
        updated_at=pydantic_graph.updated_at,
    )


# Reverse converters (SQLAlchemy to Pydantic)


def sqlalchemy_to_pydantic_user(sqlalchemy_user: UserModel) -> User:
    """Convert SQLAlchemy UserModel to Pydantic User."""
    pydantic_user = User(
        id=sqlalchemy_user.id,
        role=sqlalchemy_user.role,
        subscription_tier=sqlalchemy_user.subscription_tier,
        is_active=sqlalchemy_user.is_active,
        is_suspended=sqlalchemy_user.is_suspended,
        email_verified_at=sqlalchemy_user.email_verified_at,
        last_activity=sqlalchemy_user.last_activity,
        total_chats=sqlalchemy_user.total_chats,
        total_messages=sqlalchemy_user.total_messages,
        created_at=sqlalchemy_user.created_at,
        updated_at=sqlalchemy_user.updated_at,
        deleted_at=sqlalchemy_user.deleted_at,
        is_deleted=sqlalchemy_user.is_deleted,
        metadata=sqlalchemy_user.metadata or {},
    )

    # Add auth if present
    if sqlalchemy_user.auth:
        pydantic_user.auth = sqlalchemy_to_pydantic_user_auth(sqlalchemy_user.auth)

    # Add profile if present
    if sqlalchemy_user.profile:
        pydantic_user.profile = sqlalchemy_to_pydantic_user_profile(
            sqlalchemy_user.profile
        )

    # Add preferences if present
    if sqlalchemy_user.preferences:
        pydantic_user.preferences = sqlalchemy_to_pydantic_user_preferences(
            sqlalchemy_user.preferences
        )

    return pydantic_user


def sqlalchemy_to_pydantic_user_auth(sqlalchemy_auth: UserAuthModel) -> UserAuth:
    """Convert SQLAlchemy UserAuthModel to Pydantic UserAuth."""
    return UserAuth(
        provider=sqlalchemy_auth.provider,
        provider_id=sqlalchemy_auth.provider_id,
        email=sqlalchemy_auth.email,
        password_hash=sqlalchemy_auth.password_hash,
        is_verified=sqlalchemy_auth.is_verified,
        mfa_enabled=sqlalchemy_auth.mfa_enabled,
        mfa_secret=sqlalchemy_auth.mfa_secret,
        last_login=sqlalchemy_auth.last_login,
        failed_login_attempts=sqlalchemy_auth.failed_login_attempts,
        locked_until=sqlalchemy_auth.locked_until,
        created_at=sqlalchemy_auth.created_at,
        updated_at=sqlalchemy_auth.updated_at,
    )


def sqlalchemy_to_pydantic_user_profile(
    sqlalchemy_profile: UserProfileModel,
) -> UserProfile:
    """Convert SQLAlchemy UserProfileModel to Pydantic UserProfile."""
    return UserProfile(
        username=sqlalchemy_profile.username,
        first_name=sqlalchemy_profile.first_name,
        last_name=sqlalchemy_profile.last_name,
        display_name=sqlalchemy_profile.display_name,
        avatar_url=sqlalchemy_profile.avatar_url,
        bio=sqlalchemy_profile.bio,
        timezone=sqlalchemy_profile.timezone,
        language=sqlalchemy_profile.language,
        country=sqlalchemy_profile.country,
        created_at=sqlalchemy_profile.created_at,
        updated_at=sqlalchemy_profile.updated_at,
    )


def sqlalchemy_to_pydantic_user_preferences(
    sqlalchemy_preferences: UserPreferencesModel,
) -> UserPreferences:
    """Convert SQLAlchemy UserPreferencesModel to Pydantic UserPreferences."""
    return UserPreferences(
        email_notifications=sqlalchemy_preferences.email_notifications,
        push_notifications=sqlalchemy_preferences.push_notifications,
        sms_notifications=sqlalchemy_preferences.sms_notifications,
        default_graph=sqlalchemy_preferences.default_graph,
        auto_route=sqlalchemy_preferences.auto_route,
        chat_history_retention=sqlalchemy_preferences.chat_history_retention,
        data_sharing=sqlalchemy_preferences.data_sharing,
        profile_visibility=sqlalchemy_preferences.profile_visibility,
        theme=sqlalchemy_preferences.theme,
        compact_mode=sqlalchemy_preferences.compact_mode,
        debug_mode=sqlalchemy_preferences.debug_mode,
        beta_features=sqlalchemy_preferences.beta_features,
        created_at=sqlalchemy_preferences.created_at,
        updated_at=sqlalchemy_preferences.updated_at,
    )


def sqlalchemy_to_pydantic_chat_session(
    sqlalchemy_chat: ChatSessionModel,
) -> ChatSession:
    """Convert SQLAlchemy ChatSessionModel to Pydantic ChatSession."""
    context = None
    if sqlalchemy_chat.context:
        context = ChatContext(**sqlalchemy_chat.context)

    return ChatSession(
        id=sqlalchemy_chat.id,
        user_id=sqlalchemy_chat.user_id,
        session_id=sqlalchemy_chat.session_id,
        frontend_type=sqlalchemy_chat.frontend_type,
        status=sqlalchemy_chat.status,
        title=sqlalchemy_chat.title,
        description=sqlalchemy_chat.description,
        context=context,
        current_graph=sqlalchemy_chat.current_graph,
        message_count=sqlalchemy_chat.message_count,
        last_message_at=sqlalchemy_chat.last_message_at,
        frontend_data=sqlalchemy_chat.frontend_data,
        created_at=sqlalchemy_chat.created_at,
        updated_at=sqlalchemy_chat.updated_at,
    )


def sqlalchemy_to_pydantic_chat_message(
    sqlalchemy_message: ChatMessageModel,
) -> ChatMessage:
    """Convert SQLAlchemy ChatMessageModel to Pydantic ChatMessage."""
    return ChatMessage(
        id=sqlalchemy_message.id,
        session_id=sqlalchemy_message.session_id,
        user_id=sqlalchemy_message.user_id,
        message_type=sqlalchemy_message.message_type,
        content=sqlalchemy_message.content,
        timestamp=sqlalchemy_message.timestamp,
        graph_type=sqlalchemy_message.graph_type,
        metadata=sqlalchemy_message.message_metadata or {},
        created_at=sqlalchemy_message.created_at,
        updated_at=sqlalchemy_message.updated_at,
    )


def sqlalchemy_to_pydantic_subscription(
    sqlalchemy_subscription: SubscriptionModel,
) -> Subscription:
    """Convert SQLAlchemy SubscriptionModel to Pydantic Subscription."""
    # Note: This is a simplified conversion. In practice, you'd need to fetch the plan separately
    plan = None
    if sqlalchemy_subscription.plan:
        plan = SubscriptionPlan(
            id=sqlalchemy_subscription.plan.id,
            tier=sqlalchemy_subscription.plan.tier,
            name=sqlalchemy_subscription.plan.name,
            description=sqlalchemy_subscription.plan.description,
            price_monthly=sqlalchemy_subscription.plan.price_monthly,
            price_yearly=sqlalchemy_subscription.plan.price_yearly,
            currency=sqlalchemy_subscription.plan.currency,
            limits=UsageLimit(**sqlalchemy_subscription.plan.limits)
            if sqlalchemy_subscription.plan.limits
            else None,
            features=sqlalchemy_subscription.plan.features,
            billing_cycle=sqlalchemy_subscription.plan.billing_cycle,
            trial_days=sqlalchemy_subscription.plan.trial_days,
            is_active=sqlalchemy_subscription.plan.is_active,
            is_popular=sqlalchemy_subscription.plan.is_popular,
            created_at=sqlalchemy_subscription.plan.created_at,
            updated_at=sqlalchemy_subscription.plan.updated_at,
        )

    usage = None
    if sqlalchemy_subscription.usage:
        usage = UsageTracking(
            user_id=sqlalchemy_subscription.usage.user_id,
            subscription_tier=sqlalchemy_subscription.usage.subscription_tier,
            requests_current_minute=sqlalchemy_subscription.usage.requests_current_minute,
            requests_current_hour=sqlalchemy_subscription.usage.requests_current_hour,
            requests_current_day=sqlalchemy_subscription.usage.requests_current_day,
            requests_current_month=sqlalchemy_subscription.usage.requests_current_month,
            tokens_current_day=sqlalchemy_subscription.usage.tokens_current_day,
            tokens_current_month=sqlalchemy_subscription.usage.tokens_current_month,
            active_sessions=sqlalchemy_subscription.usage.active_sessions,
            usage_by_graph=sqlalchemy_subscription.usage.usage_by_graph,
            last_request_at=sqlalchemy_subscription.usage.last_request_at,
            last_reset_at=sqlalchemy_subscription.usage.last_reset_at,
            created_at=sqlalchemy_subscription.usage.created_at,
            updated_at=sqlalchemy_subscription.usage.updated_at,
        )

    return Subscription(
        id=sqlalchemy_subscription.id,
        user_id=sqlalchemy_subscription.user_id,
        plan=plan,
        status=sqlalchemy_subscription.status,
        is_active=sqlalchemy_subscription.is_active,
        billing_cycle=sqlalchemy_subscription.billing_cycle,
        next_billing_date=sqlalchemy_subscription.next_billing_date,
        last_billing_date=sqlalchemy_subscription.last_billing_date,
        is_trial=sqlalchemy_subscription.is_trial,
        trial_ends_at=sqlalchemy_subscription.trial_ends_at,
        payment_method_id=sqlalchemy_subscription.payment_method_id,
        stripe_subscription_id=sqlalchemy_subscription.stripe_subscription_id,
        cancelled_at=sqlalchemy_subscription.cancelled_at,
        cancellation_reason=sqlalchemy_subscription.cancellation_reason,
        usage=usage,
        created_at=sqlalchemy_subscription.created_at,
        updated_at=sqlalchemy_subscription.updated_at,
    )


def sqlalchemy_to_pydantic_graph(sqlalchemy_graph: GraphModel) -> Graph:
    """Convert SQLAlchemy GraphModel to Pydantic Graph."""
    default_config = None
    if sqlalchemy_graph.default_config:
        default_config = GraphConfig(**sqlalchemy_graph.default_config)

    instances = []
    if sqlalchemy_graph.instances:
        for instance in sqlalchemy_graph.instances:
            instances.append(
                GraphInstance(
                    id=instance.id,
                    graph_id=instance.graph_id,
                    instance_id=instance.instance_id,
                    version=instance.version,
                    endpoint=instance.endpoint,
                    region=instance.region,
                    status=instance.status,
                    config=instance.config,
                    max_capacity=instance.max_capacity,
                    current_load=instance.current_load,
                    deployment_id=instance.deployment_id,
                    container_id=instance.container_id,
                    started_at=instance.started_at,
                    last_heartbeat=instance.last_heartbeat,
                    created_at=instance.created_at,
                    updated_at=instance.updated_at,
                )
            )

    return Graph(
        id=sqlalchemy_graph.id,
        graph_type=sqlalchemy_graph.graph_type,
        name=sqlalchemy_graph.name,
        description=sqlalchemy_graph.description,
        version=sqlalchemy_graph.version,
        author=sqlalchemy_graph.author,
        tags=sqlalchemy_graph.tags,
        status=sqlalchemy_graph.status,
        is_available=sqlalchemy_graph.is_available,
        default_config=default_config,
        total_requests=sqlalchemy_graph.total_requests,
        total_users=sqlalchemy_graph.total_users,
        last_deployment=sqlalchemy_graph.last_deployment,
        instances=instances,
        created_at=sqlalchemy_graph.created_at,
        updated_at=sqlalchemy_graph.updated_at,
    )
