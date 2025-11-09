"""
Error context management for BotsPool

This module provides utilities for managing error context information,
including request tracking, user information, and debugging data.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Union
from uuid import UUID

from .error_codes import ErrorCode, ErrorCategory


class ErrorContext:
    """
    Error context information.

    Stores contextual information about errors for debugging and monitoring.
    """

    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[Union[str, UUID]] = None,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        graph_type: Optional[str] = None,
        frontend_type: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ):
        self.request_id = request_id
        self.user_id = str(user_id) if user_id else None
        self.session_id = session_id
        self.conversation_id = conversation_id
        self.graph_type = graph_type
        self.frontend_type = frontend_type
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.endpoint = endpoint
        self.method = method
        self.timestamp = timestamp or datetime.utcnow()
        self.additional_data = additional_data or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert error context to dictionary."""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "graph_type": self.graph_type,
            "frontend_type": self.frontend_type,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "endpoint": self.endpoint,
            "method": self.method,
            "timestamp": self.timestamp.isoformat(),
            "additional_data": self.additional_data,
        }

    def add_data(self, key: str, value: Any) -> None:
        """Add additional data to the context."""
        self.additional_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get additional data from the context."""
        return self.additional_data.get(key, default)

    def sanitize_for_logging(self) -> Dict[str, Any]:
        """Get sanitized context for logging (removes sensitive data)."""
        sanitized = self.to_dict()

        # Remove or mask sensitive information
        if sanitized.get("ip_address"):
            # Mask IP address for privacy
            ip = sanitized["ip_address"]
            if "." in ip:  # IPv4
                parts = ip.split(".")
                sanitized["ip_address"] = f"{parts[0]}.{parts[1]}.xxx.xxx"
            elif ":" in ip:  # IPv6
                sanitized["ip_address"] = "xxxx:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx"

        # Remove user agent details
        if sanitized.get("user_agent"):
            sanitized["user_agent"] = "REDACTED"

        return sanitized


def create_error_context(
    request_id: Optional[str] = None,
    user_id: Optional[Union[str, UUID]] = None,
    **kwargs,
) -> ErrorContext:
    """
    Create an error context with the provided information.

    Args:
        request_id: Unique request identifier
        user_id: User identifier
        **kwargs: Additional context information

    Returns:
        ErrorContext instance
    """
    return ErrorContext(request_id=request_id, user_id=user_id, **kwargs)


def add_error_context(error: Exception, context: ErrorContext) -> Exception:
    """
    Add error context to an exception.

    Args:
        error: The exception to add context to
        context: Error context information

    Returns:
        The exception with added context
    """
    if hasattr(error, "error_context"):
        # Merge with existing context
        existing_context = error.error_context
        for key, value in context.to_dict().items():
            if value is not None and not hasattr(existing_context, key):
                setattr(existing_context, key, value)
    else:
        # Add new context
        error.error_context = context

    return error


def extract_error_context(error: Exception) -> Optional[ErrorContext]:
    """
    Extract error context from an exception.

    Args:
        error: The exception to extract context from

    Returns:
        ErrorContext if available, None otherwise
    """
    return getattr(error, "error_context", None)


def format_error_context_for_logging(error: Exception) -> Dict[str, Any]:
    """
    Format error context for logging.

    Args:
        error: The exception to format context for

    Returns:
        Dictionary with sanitized context information
    """
    context = extract_error_context(error)
    if context:
        return context.sanitize_for_logging()
    return {}


def format_error_context_for_api(error: Exception) -> Dict[str, Any]:
    """
    Format error context for API responses.

    Args:
        error: The exception to format context for

    Returns:
        Dictionary with API-safe context information
    """
    context = extract_error_context(error)
    if context:
        return {
            "request_id": context.request_id,
            "timestamp": context.timestamp.isoformat(),
            "graph_type": context.graph_type,
            "frontend_type": context.frontend_type,
        }
    return {}


class ErrorContextManager:
    """
    Context manager for error context.

    Provides a way to automatically add context to exceptions raised within a block.
    """

    def __init__(self, **context_kwargs):
        self.context = create_error_context(**context_kwargs)
        self.original_context = None

    def __enter__(self):
        # Store any existing context
        import sys

        if hasattr(sys, "_getframe"):
            frame = sys._getframe(1)
            if "error_context" in frame.f_locals:
                self.original_context = frame.f_locals["error_context"]

        return self.context

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val and isinstance(exc_val, Exception):
            # Add context to the exception
            add_error_context(exc_val, self.context)

        return False  # Don't suppress the exception


# Global error context storage for request-scoped context
_error_context_storage: Dict[str, ErrorContext] = {}


def set_global_error_context(request_id: str, context: ErrorContext) -> None:
    """
    Set global error context for a request.

    Args:
        request_id: Request identifier
        context: Error context
    """
    _error_context_storage[request_id] = context


def get_global_error_context(request_id: str) -> Optional[ErrorContext]:
    """
    Get global error context for a request.

    Args:
        request_id: Request identifier

    Returns:
        ErrorContext if available, None otherwise
    """
    return _error_context_storage.get(request_id)


def clear_global_error_context(request_id: str) -> None:
    """
    Clear global error context for a request.

    Args:
        request_id: Request identifier
    """
    _error_context_storage.pop(request_id, None)


def get_current_error_context() -> Optional[ErrorContext]:
    """
    Get the current error context from the global storage.

    This is a simplified version that assumes a single active request.
    In a real application, you'd use request-scoped storage.

    Returns:
        Current ErrorContext if available, None otherwise
    """
    if _error_context_storage:
        # Return the most recent context
        return max(_error_context_storage.values(), key=lambda c: c.timestamp)
    return None
