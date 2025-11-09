"""
Enums for BotsPool models

This module contains all the enumeration types used across the BotsPool platform.
Enums provide type safety and ensure consistent values across the system.
"""

from enum import Enum


class SubscriptionTier(str, Enum):
    """Subscription tier levels for users."""

    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class GraphType(str, Enum):
    """Available AI graph types."""

    TODO = "todo"
    EMAIL = "email"
    CALENDAR = "calendar"
    DOCUMENT = "document"
    CODE = "code"
    RESEARCH = "research"


class UserRole(str, Enum):
    """User roles in the system."""

    USER = "user"  # Generic user role
    FREE_USER = "free_user"
    BASIC_USER = "basic_user"
    PREMIUM_USER = "premium_user"
    ENTERPRISE_USER = "enterprise_user"
    ADMIN = "admin"
    DEVELOPER = "developer"


class Permission(str, Enum):
    """System permissions."""

    # Graph permissions
    READ_GRAPHS = "read_graphs"
    WRITE_GRAPHS = "write_graphs"
    ADMIN_GRAPHS = "admin_graphs"

    # User permissions
    MANAGE_USERS = "manage_users"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_SUBSCRIPTIONS = "manage_subscriptions"

    # System permissions
    SYSTEM_ADMIN = "system_admin"
    VIEW_LOGS = "view_logs"
    MANAGE_INFRASTRUCTURE = "manage_infrastructure"


class ChatStatus(str, Enum):
    """Chat session status."""

    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    ERROR = "error"


class GraphStatus(str, Enum):
    """Graph instance status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


class GraphHealthStatus(str, Enum):
    """Graph health status for monitoring."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ErrorSeverity(str, Enum):
    """Error severity levels for prioritization and handling."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TokenType(str, Enum):
    """Token types for authentication."""

    ACCESS = "access"
    REFRESH = "refresh"
    MFA = "mfa"
    PASSWORD_RESET = "password_reset"


class FrontendType(str, Enum):
    """Frontend application types."""

    TELEGRAM = "telegram"
    DISCORD = "discord"
    WEB = "web"
    MOBILE = "mobile"
    API = "api"


class AuthProvider(str, Enum):
    """Authentication providers."""

    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"


class MessageType(str, Enum):
    """Chat message types."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ERROR = "error"


class TaskPriority(str, Enum):
    """Task priority levels (for ToDo graph)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    """Task status (for ToDo graph)."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventType(str, Enum):
    """Event types (for Calendar graph)."""

    MEETING = "meeting"
    APPOINTMENT = "appointment"
    REMINDER = "reminder"
    DEADLINE = "deadline"
    PERSONAL = "personal"


class EmailType(str, Enum):
    """Email types (for Email graph)."""

    COMPOSE = "compose"
    REPLY = "reply"
    FORWARD = "forward"
    TEMPLATE = "template"


class DocumentType(str, Enum):
    """Document types (for Document graph)."""

    TEXT = "text"
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    PRESENTATION = "presentation"


class CodeLanguage(str, Enum):
    """Programming languages (for Code graph)."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    PHP = "php"
    RUBY = "ruby"


class ResearchDomain(str, Enum):
    """Research domains (for Research graph)."""

    TECHNOLOGY = "technology"
    SCIENCE = "science"
    BUSINESS = "business"
    ACADEMIC = "academic"
    NEWS = "news"
    GENERAL = "general"


class ErrorCategory(str, Enum):
    """Error categories for classification and handling."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    GRAPH_SERVICE = "graph_service"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    RATE_LIMIT = "rate_limit"
    SERVER = "server"
    UNKNOWN = "unknown"
    CONFIGURATION = "configuration"


class ChatMessageType(str, Enum):
    """Chat message types."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ERROR = "error"


class HealthStatus(str, Enum):
    """Health status for monitoring."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CacheStrategy(str, Enum):
    """Cache strategies for data management."""

    NO_CACHE = "no_cache"
    READ_THROUGH = "read_through"
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    CACHE_ASIDE = "cache_aside"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
