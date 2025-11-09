"""
Custom log formatters for structured logging
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
import sys


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._exclude_fields = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON.

        Args:
            record: Log record to format

        Returns:
            str: JSON-formatted log entry
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in self._exclude_fields and not key.startswith("_"):
                log_entry[key] = value

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for development logging.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._colors = {
            "DEBUG": "\033[36m",  # Cyan
            "INFO": "\033[32m",  # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",  # Red
            "CRITICAL": "\033[35m",  # Magenta
            "RESET": "\033[0m",  # Reset
        }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record for human reading.

        Args:
            record: Log record to format

        Returns:
            str: Human-readable log entry
        """
        # Get the base formatted message
        message = super().format(record)

        # Add colors if outputting to terminal
        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            color = self._colors.get(record.levelname, "")
            reset = self._colors["RESET"]
            message = f"{color}{message}{reset}"

        return message


class CustomFormatter(logging.Formatter):
    """
    Custom formatter with configurable fields.
    """

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        include_extra: bool = True,
        **kwargs,
    ):
        """
        Initialize the custom formatter.

        Args:
            fmt: Format string
            datefmt: Date format string
            include_extra: Whether to include extra fields
        """
        if fmt is None:
            fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

        super().__init__(fmt, datefmt, **kwargs)
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record with custom formatting.

        Args:
            record: Log record to format

        Returns:
            str: Formatted log entry
        """
        # Get the base formatted message
        message = super().format(record)

        # Add extra fields if requested
        if self.include_extra:
            extra_fields = []
            for key, value in record.__dict__.items():
                if key not in {
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                }:
                    extra_fields.append(f"{key}={value}")

            if extra_fields:
                message += f" | {' | '.join(extra_fields)}"

        return message


class SecurityFormatter(logging.Formatter):
    """
    Specialized formatter for security-related logs.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sensitive_fields = {"password", "token", "key", "secret", "auth"}

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a security log record, masking sensitive information.

        Args:
            record: Log record to format

        Returns:
            str: Formatted security log entry
        """
        # Get the base formatted message
        message = super().format(record)

        # Mask sensitive fields in extra data
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if any(
                    sensitive in key.lower() for sensitive in self._sensitive_fields
                ):
                    if isinstance(value, str) and len(value) > 4:
                        masked_value = value[:2] + "*" * (len(value) - 4) + value[-2:]
                        message = message.replace(str(value), masked_value)

        return message


class PerformanceFormatter(logging.Formatter):
    """
    Specialized formatter for performance-related logs.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a performance log record.

        Args:
            record: Log record to format

        Returns:
            str: Formatted performance log entry
        """
        # Get the base formatted message
        message = super().format(record)

        # Add performance metrics if present
        if hasattr(record, "execution_time"):
            message += f" | execution_time={record.execution_time}ms"

        if hasattr(record, "memory_usage"):
            message += f" | memory_usage={record.memory_usage}MB"

        if hasattr(record, "cpu_usage"):
            message += f" | cpu_usage={record.cpu_usage}%"

        return message
