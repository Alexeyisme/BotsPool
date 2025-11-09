"""
BotsPool Shared Models

This module contains all the core data models used across the BotsPool platform.
Models are built with Pydantic for validation, serialization, and documentation.
"""

from .base import BaseModel, TimestampMixin, MetadataMixin
from .enums import (
    SubscriptionTier,
    GraphType,
    UserRole,
    Permission,
    ChatStatus,
    GraphStatus,
    GraphHealthStatus,
    CircuitState,
    ErrorSeverity,
    TokenType,
    FrontendType,
    AuthProvider,
    MessageType,
    TaskPriority,
    TaskStatus,
    EventType,
    EmailType,
    DocumentType,
    CodeLanguage,
    ResearchDomain,
    ErrorCategory,
    ChatMessageType,
    HealthStatus,
    CacheStrategy,
    LogLevel,
)
from .user import User, UserProfile, UserPreferences, UserSession, UserAuth
from .chat import ChatRequest, ChatResponse, ChatSession, ChatMessage, ChatContext
from .subscription import Subscription, SubscriptionPlan, UsageLimit, UsageTracking
from .graph import Graph, GraphInstance, GraphHealth, GraphConfig
from .session import SessionBase, SessionCreate, SessionUpdate, SessionRecord

__all__ = [
    # Base models
    "BaseModel",
    "TimestampMixin",
    "MetadataMixin",
    # Enums
    "SubscriptionTier",
    "GraphType",
    "UserRole",
    "Permission",
    "ChatStatus",
    "GraphStatus",
    "GraphHealthStatus",
    "CircuitState",
    "ErrorSeverity",
    "TokenType",
    "FrontendType",
    "AuthProvider",
    "MessageType",
    "TaskPriority",
    "TaskStatus",
    "EventType",
    "EmailType",
    "DocumentType",
    "CodeLanguage",
    "ResearchDomain",
    "ErrorCategory",
    "ChatMessageType",
    "HealthStatus",
    "CacheStrategy",
    "LogLevel",
    # User models
    "User",
    "UserProfile",
    "UserPreferences",
    "UserSession",
    "UserAuth",
    # Chat models
    "ChatRequest",
    "ChatResponse",
    "ChatSession",
    "ChatMessage",
    "ChatContext",
    # Subscription models
    "Subscription",
    "SubscriptionPlan",
    "UsageLimit",
    "UsageTracking",
    # Graph models
    "Graph",
    "GraphInstance",
    "GraphHealth",
    "GraphConfig",
    # Session models
    "SessionBase",
    "SessionCreate",
    "SessionUpdate",
    "SessionRecord",
]
