"""
Error handling utilities for BotsPool

This module provides utilities for handling errors consistently across
the BotsPool platform, including formatting, logging, and response generation.
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Union

from .exceptions import BotsPoolError
from .error_codes import (
    ErrorCode,
    ErrorCategory,
    is_retryable_error,
    get_retry_after_seconds,
)
from .error_context import (
    ErrorContext,
    extract_error_context,
    format_error_context_for_logging,
)


class ErrorHandler:
    """
    Centralized error handler for the BotsPool platform.

    Provides consistent error handling, logging, and response formatting.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def handle_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        include_traceback: bool = False,
    ) -> Dict[str, Any]:
        """
        Handle an error and return a formatted response.

        Args:
            error: The exception to handle
            context: Additional error context
            include_traceback: Whether to include traceback in response

        Returns:
            Formatted error response dictionary
        """
        # Extract context from error if not provided
        if context is None:
            context = extract_error_context(error)

        # Log the error
        self.log_error(error, context, include_traceback)

        # Format the response
        return self.format_error_response(error, context, include_traceback)

    def log_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        include_traceback: bool = True,
    ) -> None:
        """
        Log an error with appropriate level and context.

        Args:
            error: The exception to log
            context: Additional error context
            include_traceback: Whether to include traceback in log
        """
        # Determine log level based on error type
        log_level = self._get_log_level(error)

        # Prepare log message
        message = f"Error: {str(error)}"

        # Add context information
        if context:
            context_data = format_error_context_for_logging(error)
            if context_data:
                message += f" | Context: {context_data}"

        # Add error code if available
        if isinstance(error, BotsPoolError) and error.error_code:
            message += f" | Code: {error.error_code.value}"

        # Log with appropriate level
        if include_traceback:
            self.logger.log(log_level, message, exc_info=True)
        else:
            self.logger.log(log_level, message)

    def format_error_response(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        include_traceback: bool = False,
    ) -> Dict[str, Any]:
        """
        Format an error for API response.

        Args:
            error: The exception to format
            context: Additional error context
            include_traceback: Whether to include traceback in response

        Returns:
            Formatted error response dictionary
        """
        if isinstance(error, BotsPoolError):
            # Use the error's built-in formatting
            response = error.to_dict()
        else:
            # Format unknown errors
            response = self._format_unknown_error(error)

        # Add context information
        if context:
            context_data = {
                "request_id": context.request_id,
                "timestamp": context.timestamp.isoformat(),
                "graph_type": context.graph_type,
                "frontend_type": context.frontend_type,
            }
            response["error"]["context"] = context_data

        # Add traceback if requested (for development)
        if include_traceback:
            response["error"]["traceback"] = traceback.format_exc()

        return response

    def _get_log_level(self, error: Exception) -> int:
        """Get appropriate log level for an error."""
        if isinstance(error, BotsPoolError):
            if error.error_category == ErrorCategory.AUTHENTICATION:
                return logging.WARNING
            elif error.error_category == ErrorCategory.VALIDATION:
                return logging.INFO
            elif error.error_category == ErrorCategory.RATE_LIMIT:
                return logging.WARNING
            elif error.error_category == ErrorCategory.EXTERNAL_SERVICE:
                return logging.ERROR
            elif error.error_category == ErrorCategory.DATABASE:
                return logging.ERROR
            elif error.error_category == ErrorCategory.INTERNAL:
                return logging.CRITICAL
            else:
                return logging.ERROR
        else:
            return logging.CRITICAL

    def _format_unknown_error(self, error: Exception) -> Dict[str, Any]:
        """Format an unknown error."""
        return {
            "error": {
                "code": "UNKNOWN_ERROR_001",
                "message": "An unexpected error occurred",
                "category": "UNKNOWN",
                "details": {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                },
                "retryable": False,
                "retry_after": None,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": None,
                "request_id": None,
            }
        }


def format_error_response(
    error: Exception,
    context: Optional[ErrorContext] = None,
    include_traceback: bool = False,
) -> Dict[str, Any]:
    """
    Format an error for API response.

    Convenience function for formatting errors without creating an ErrorHandler instance.

    Args:
        error: The exception to format
        context: Additional error context
        include_traceback: Whether to include traceback in response

    Returns:
        Formatted error response dictionary
    """
    handler = ErrorHandler()
    return handler.format_error_response(error, context, include_traceback)


def log_error(
    error: Exception,
    context: Optional[ErrorContext] = None,
    include_traceback: bool = True,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Log an error with appropriate level and context.

    Convenience function for logging errors without creating an ErrorHandler instance.

    Args:
        error: The exception to log
        context: Additional error context
        include_traceback: Whether to include traceback in log
        logger: Logger to use (defaults to module logger)
    """
    handler = ErrorHandler(logger)
    handler.log_error(error, context, include_traceback)


def handle_error(
    error: Exception,
    context: Optional[ErrorContext] = None,
    include_traceback: bool = False,
) -> Dict[str, Any]:
    """
    Handle an error and return a formatted response.

    Convenience function for handling errors without creating an ErrorHandler instance.

    Args:
        error: The exception to handle
        context: Additional error context
        include_traceback: Whether to include traceback in response

    Returns:
        Formatted error response dictionary
    """
    handler = ErrorHandler()
    return handler.handle_error(error, context, include_traceback)


class ErrorResponseFormatter:
    """
    Utility class for formatting error responses for different environments.
    """

    @staticmethod
    def format_for_development(
        error: Exception, context: Optional[ErrorContext] = None
    ) -> Dict[str, Any]:
        """Format error response for development environment."""
        handler = ErrorHandler()
        return handler.format_error_response(error, context, include_traceback=True)

    @staticmethod
    def format_for_production(
        error: Exception, context: Optional[ErrorContext] = None
    ) -> Dict[str, Any]:
        """Format error response for production environment."""
        handler = ErrorHandler()
        response = handler.format_error_response(
            error, context, include_traceback=False
        )

        # Sanitize sensitive information for production
        if isinstance(error, BotsPoolError):
            # Remove internal details
            if "details" in response["error"]:
                details = response["error"]["details"]
                # Keep only safe details
                safe_details = {}
                for key, value in details.items():
                    if key in ["field", "limit_type", "limit_value", "current_usage"]:
                        safe_details[key] = value
                response["error"]["details"] = safe_details

        return response

    @staticmethod
    def format_for_api(
        error: Exception, context: Optional[ErrorContext] = None
    ) -> Dict[str, Any]:
        """Format error response for API consumption."""
        handler = ErrorHandler()
        response = handler.format_error_response(
            error, context, include_traceback=False
        )

        # Ensure API-friendly format
        if "error" in response:
            error_data = response["error"]

            # Add HTTP status code suggestion
            if isinstance(error, BotsPoolError):
                error_data["http_status"] = _get_http_status_code(error.error_category)

            # Add retry information
            if isinstance(error, BotsPoolError) and error.retryable:
                error_data["retryable"] = True
                if error.retry_after:
                    error_data["retry_after"] = error.retry_after
            else:
                error_data["retryable"] = False

        return response


def _get_http_status_code(category: ErrorCategory) -> int:
    """Get suggested HTTP status code for error category."""
    status_codes = {
        ErrorCategory.AUTHENTICATION: 401,
        ErrorCategory.AUTHORIZATION: 403,
        ErrorCategory.VALIDATION: 422,
        ErrorCategory.GRAPH: 503,
        ErrorCategory.DATABASE: 503,
        ErrorCategory.EXTERNAL_SERVICE: 502,
        ErrorCategory.RATE_LIMIT: 429,
        ErrorCategory.SUBSCRIPTION: 403,
        ErrorCategory.CONFIGURATION: 500,
        ErrorCategory.INTERNAL: 500,
        ErrorCategory.UNKNOWN: 500,
    }
    return status_codes.get(category, 500)


class ErrorMetrics:
    """
    Utility class for collecting error metrics.
    """

    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_categories: Dict[str, int] = {}
        self.error_timestamps: Dict[str, list] = {}

    def record_error(self, error: Exception) -> None:
        """Record an error for metrics collection."""
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        if isinstance(error, BotsPoolError) and error.error_category:
            category = error.error_category.value
            self.error_categories[category] = self.error_categories.get(category, 0) + 1

        # Record timestamp
        timestamp = datetime.utcnow().isoformat()
        if error_type not in self.error_timestamps:
            self.error_timestamps[error_type] = []
        self.error_timestamps[error_type].append(timestamp)

        # Keep only recent timestamps (last 100)
        if len(self.error_timestamps[error_type]) > 100:
            self.error_timestamps[error_type] = self.error_timestamps[error_type][-100:]

    def get_metrics(self) -> Dict[str, Any]:
        """Get error metrics."""
        return {
            "error_counts": self.error_counts.copy(),
            "error_categories": self.error_categories.copy(),
            "total_errors": sum(self.error_counts.values()),
            "unique_error_types": len(self.error_counts),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def reset_metrics(self) -> None:
        """Reset error metrics."""
        self.error_counts.clear()
        self.error_categories.clear()
        self.error_timestamps.clear()


# Global error metrics instance
_error_metrics = ErrorMetrics()


def record_error_metrics(error: Exception) -> None:
    """Record error metrics globally."""
    _error_metrics.record_error(error)


def get_error_metrics() -> Dict[str, Any]:
    """Get global error metrics."""
    return _error_metrics.get_metrics()


def reset_error_metrics() -> None:
    """Reset global error metrics."""
    _error_metrics.reset_metrics()
