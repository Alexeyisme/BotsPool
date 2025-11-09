"""
BotsPool Error Handling

This module provides comprehensive error handling for the BotsPool platform,
including custom exceptions, error codes, and error handling utilities.
"""

from .exceptions import (
    BotsPoolError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    GraphError,
    GraphServiceError,
    DatabaseError,
    ExternalServiceError,
    RateLimitError,
    SubscriptionError,
    ConfigurationError,
    TokenExpiredError,
    InvalidTokenError,
    InsufficientPermissionsError,
    GraphUnavailableError,
    GraphTimeoutError,
    DatabaseConnectionError,
    DatabaseQueryError,
    OpenAIServiceError,
    RedisServiceError,
    PostgresServiceError,
    RateLimitExceededError,
    SubscriptionLimitExceededError,
    InvalidConfigurationError,
    MissingConfigurationError,
    ServerError,
)

from .error_codes import (
    ErrorCode,
    ErrorCategory,
    ErrorSeverity,
    get_error_code,
    get_error_category,
    is_retryable_error,
    get_retry_after_seconds,
)

from .error_context import ErrorContext, create_error_context, add_error_context

from .error_handler import ErrorHandler, format_error_response, log_error, handle_error

__all__ = [
    # Base exceptions
    "BotsPoolError",
    # Authentication & Authorization
    "AuthenticationError",
    "AuthorizationError",
    "TokenExpiredError",
    "InvalidTokenError",
    "InsufficientPermissionsError",
    # Validation
    "ValidationError",
    # Graph errors
    "GraphError",
    "GraphServiceError",
    "GraphUnavailableError",
    "GraphTimeoutError",
    # Database errors
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    # External service errors
    "ExternalServiceError",
    "OpenAIServiceError",
    "RedisServiceError",
    "PostgresServiceError",
    # Rate limiting
    "RateLimitError",
    "RateLimitExceededError",
    # Subscription
    "SubscriptionError",
    "SubscriptionLimitExceededError",
    # Configuration
    "ConfigurationError",
    "InvalidConfigurationError",
    "MissingConfigurationError",
    "ServerError",
    # Error utilities
    "ErrorCode",
    "ErrorCategory",
    "ErrorSeverity",
    "get_error_code",
    "get_error_category",
    "is_retryable_error",
    "get_retry_after_seconds",
    # Error context
    "ErrorContext",
    "create_error_context",
    "add_error_context",
    # Error handling
    "ErrorHandler",
    "format_error_response",
    "log_error",
    "handle_error",
]
