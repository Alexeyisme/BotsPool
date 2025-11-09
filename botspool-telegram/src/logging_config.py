"""Structured logging configuration"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "telegram-bot",
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "telegram_user_id"):
            log_entry["telegram_user_id"] = record.telegram_user_id
        if hasattr(record, "chat_id"):
            log_entry["chat_id"] = record.chat_id
        if hasattr(record, "agent"):
            log_entry["agent"] = record.agent

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Setup structured logging for the bot"""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove any existing handlers
    logger.handlers.clear()

    # Create console handler with structured formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)

    return logger
