"""
Custom exceptions for BotsPool

This module defines the exception hierarchy and specific exception types
used throughout the BotsPool platform.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Union
from uuid import UUID

from .error_codes import ErrorCode, ErrorCategory, ErrorSeverity


class BotsPoolError(Exception):
    """
    Base exception class for all BotsPool errors.

    All custom exceptions in the BotsPool platform inherit from this class.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[ErrorCode] = None,
        error_category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        request_id: Optional[str] = None,
        retryable: bool = False,
        retry_after: Optional[int] = None,
        retry_after_seconds: Optional[int] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(message)

        self.message = message
        self.error_code = error_code
        self.error_category = error_category
        self.severity = severity or ErrorSeverity.MEDIUM
        self.details = details or {}
        self.user_id = str(user_id) if user_id else None
        self.request_id = request_id
        self.retryable = retryable
        self.retry_after = retry_after or retry_after_seconds
        self.retry_after_seconds = retry_after_seconds or retry_after
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": {
                "code": self.error_code.value if self.error_code else "UNKNOWN_ERROR",
                "message": self.message,
                "category": self.error_category.value
                if self.error_category
                else "UNKNOWN",
                "severity": self.severity.value if self.severity else "medium",
                "details": self.details,
                "retryable": self.retryable,
                "retry_after": self.retry_after,
                "retry_after_seconds": self.retry_after_seconds,
                "timestamp": self.timestamp.isoformat(),
                "user_id": self.user_id,
                "request_id": self.request_id,
            }
        }

    def __str__(self) -> str:
        """String representation of the error."""
        code = self.error_code.value if self.error_code else "UNKNOWN_ERROR"
        severity = self.severity.value if self.severity else "medium"
        category = self.error_category.value if self.error_category else "unknown"
        return f"[{code}] {self.message} (Severity: {severity}, Category: {category})"


# Authentication & Authorization Errors


class AuthenticationError(BotsPoolError):
    """Base class for authentication-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class AuthorizationError(BotsPoolError):
    """Base class for authorization-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has expired."""

    def __init__(self, **kwargs):
        super().__init__(
            "Authentication token has expired",
            error_code=ErrorCode.AUTH_TOKEN_EXPIRED_001,
            retryable=False,
            **kwargs,
        )


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT token is invalid or malformed."""

    def __init__(self, **kwargs):
        super().__init__(
            "Invalid authentication token",
            error_code=ErrorCode.AUTH_INVALID_TOKEN_002,
            retryable=False,
            **kwargs,
        )


class InsufficientPermissionsError(AuthorizationError):
    """Raised when user lacks required permissions."""

    def __init__(self, required_permission: str, **kwargs):
        super().__init__(
            f"Insufficient permissions. Required: {required_permission}",
            error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS_003,
            details={"required_permission": required_permission},
            retryable=False,
            **kwargs,
        )


# Validation Errors


class ValidationError(BotsPoolError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field

        # Allow error_code to be overridden
        error_code = kwargs.pop("error_code", ErrorCode.VALIDATION_INVALID_INPUT_001)

        super().__init__(
            message,
            error_code=error_code,
            error_category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            retryable=False,
            **kwargs,
        )


# Graph Errors


class GraphError(BotsPoolError):
    """Base class for graph-related errors."""

    def __init__(self, message: str, graph_type: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if graph_type:
            details["graph_type"] = graph_type

        super().__init__(
            message, error_category=ErrorCategory.GRAPH, details=details, **kwargs
        )


class GraphServiceError(BotsPoolError):
    """Base class for graph service errors."""

    def __init__(
        self,
        message: str,
        graph_type: Optional[str] = None,
        retry_after_seconds: int = 5,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if graph_type:
            details["graph_type"] = graph_type

        # Remove conflicting parameters from kwargs
        kwargs.pop("retryable", None)

        super().__init__(
            message,
            error_category=ErrorCategory.GRAPH,
            severity=ErrorSeverity.HIGH,
            retryable=True,
            retry_after_seconds=retry_after_seconds,
            details=details,
            **kwargs,
        )


class GraphUnavailableError(GraphError):
    """Raised when a graph service is unavailable."""

    def __init__(self, graph_type: str, **kwargs):
        super().__init__(
            f"Graph service '{graph_type}' is currently unavailable",
            graph_type=graph_type,
            error_code=ErrorCode.GRAPH_SERVICE_UNAVAILABLE_001,
            retryable=True,
            retry_after=30,
            **kwargs,
        )


class GraphTimeoutError(GraphError):
    """Raised when a graph request times out."""

    def __init__(self, graph_type: str, timeout_seconds: int, **kwargs):
        super().__init__(
            f"Graph request to '{graph_type}' timed out after {timeout_seconds} seconds",
            graph_type=graph_type,
            error_code=ErrorCode.GRAPH_REQUEST_TIMEOUT_002,
            details={"timeout_seconds": timeout_seconds},
            retryable=True,
            retry_after=10,
            **kwargs,
        )


# Database Errors


class DatabaseError(BotsPoolError):
    """Base class for database-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.CRITICAL,
            retryable=True,
            retry_after_seconds=kwargs.pop("retry_after_seconds", 5),
            **kwargs,
        )


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""

    def __init__(self, **kwargs):
        super().__init__(
            "Failed to connect to database",
            error_code=ErrorCode.DATABASE_CONNECTION_FAILED_001,
            retry_after_seconds=5,
            **kwargs,
        )


class DatabaseQueryError(DatabaseError):
    """Raised when a database query fails."""

    def __init__(self, query: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if query:
            details["query"] = query

        super().__init__(
            "Database query failed",
            error_code=ErrorCode.DATABASE_QUERY_FAILED_002,
            details=details,
            retry_after_seconds=2,
            **kwargs,
        )


# External Service Errors


class ExternalServiceError(BotsPoolError):
    """Base class for external service errors."""

    def __init__(self, message: str, service_name: str, **kwargs):
        details = kwargs.pop("details", {})
        details["service_name"] = service_name

        super().__init__(
            message,
            error_category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            retryable=True,
            retry_after_seconds=5,
            details=details,
            **kwargs,
        )


class OpenAIServiceError(ExternalServiceError):
    """Raised when OpenAI API calls fail."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            f"OpenAI service error: {message}",
            service_name="openai",
            error_code=ErrorCode.EXTERNAL_OPENAI_ERROR_001,
            retryable=True,
            retry_after=5,
            **kwargs,
        )


class RedisServiceError(ExternalServiceError):
    """Raised when Redis operations fail."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            f"Redis service error: {message}",
            service_name="redis",
            error_code=ErrorCode.EXTERNAL_REDIS_ERROR_001,
            retryable=True,
            retry_after=2,
            **kwargs,
        )


class PostgresServiceError(ExternalServiceError):
    """Raised when PostgreSQL operations fail."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            f"PostgreSQL service error: {message}",
            service_name="postgresql",
            error_code=ErrorCode.EXTERNAL_POSTGRES_ERROR_001,
            retryable=True,
            retry_after=3,
            **kwargs,
        )


# Rate Limiting Errors


class RateLimitError(BotsPoolError):
    """Base class for rate limiting errors."""

    def __init__(self, message: str, retry_after_seconds: int = 60, **kwargs):
        # Remove conflicting parameters from kwargs
        kwargs.pop("retryable", None)
        kwargs.pop("retry_after_seconds", None)

        super().__init__(
            message,
            error_category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            retryable=True,
            retry_after_seconds=retry_after_seconds,
            **kwargs,
        )


class RateLimitExceededError(RateLimitError):
    """Raised when rate limit is exceeded."""

    def __init__(self, limit_type: str, limit_value: int, current_usage: int, **kwargs):
        super().__init__(
            f"Rate limit exceeded for {limit_type}: {current_usage}/{limit_value}",
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED_001,
            details={
                "limit_type": limit_type,
                "limit_value": limit_value,
                "current_usage": current_usage,
            },
            retryable=True,
            retry_after=60,
            **kwargs,
        )


# Subscription Errors


class SubscriptionError(BotsPoolError):
    """Base class for subscription-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_category=ErrorCategory.SUBSCRIPTION, **kwargs)


class SubscriptionLimitExceededError(SubscriptionError):
    """Raised when subscription limits are exceeded."""

    def __init__(self, limit_type: str, limit_value: int, current_usage: int, **kwargs):
        super().__init__(
            f"Subscription limit exceeded for {limit_type}: {current_usage}/{limit_value}",
            error_code=ErrorCode.SUBSCRIPTION_LIMIT_EXCEEDED_001,
            details={
                "limit_type": limit_type,
                "limit_value": limit_value,
                "current_usage": current_usage,
            },
            retryable=False,
            **kwargs,
        )


# Configuration Errors


class ConfigurationError(BotsPoolError):
    """Base class for configuration-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            retryable=False,
            **kwargs,
        )


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration is invalid."""

    def __init__(self, config_key: str, config_value: Any, **kwargs):
        super().__init__(
            f"Invalid configuration for '{config_key}': {config_value}",
            error_code=ErrorCode.CONFIG_INVALID_VALUE_001,
            details={"config_key": config_key, "config_value": str(config_value)},
            retryable=False,
            **kwargs,
        )


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""

    def __init__(self, config_key: str, **kwargs):
        super().__init__(
            f"Missing required configuration: {config_key}",
            error_code=ErrorCode.CONFIG_MISSING_VALUE_002,
            details={"config_key": config_key},
            retryable=False,
            **kwargs,
        )


class ServerError(BotsPoolError):
    """Exception for internal server errors."""

    def __init__(self, message: str, **kwargs):
        details = kwargs.pop("details", {})
        super().__init__(
            message,
            error_category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.CRITICAL,
            retryable=False,
            details=details,
            **kwargs,
        )
