"""
Logging configuration for different environments
"""

import logging
import logging.config
import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path

from .formatters import JSONFormatter, HumanReadableFormatter
from logging.handlers import RotatingFileHandler
from logging import StreamHandler


def setup_logging(
    level: str = "INFO",
    environment: str = "development",
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
) -> None:
    """
    Set up logging configuration for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Environment (development, production, test)
        log_file: Log file path (optional)
        log_dir: Log directory path (optional)
    """
    if environment == "development":
        configure_development_logging(level, log_file)
    elif environment == "production":
        configure_production_logging(level, log_file, log_dir)
    elif environment == "test":
        configure_test_logging(level)
    else:
        raise ValueError(f"Unknown environment: {environment}")


def configure_development_logging(
    level: str = "DEBUG", log_file: Optional[str] = None
) -> None:
    """
    Configure logging for development environment.

    Args:
        level: Log level
        log_file: Optional log file path
    """
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "human": {
                "()": HumanReadableFormatter,
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": JSONFormatter,
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "human",
                "stream": sys.stdout,
            }
        },
        "loggers": {
            "": {"level": level, "handlers": ["console"], "propagate": False},
            "botspool_shared_utils": {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    # Add file handler if specified
    if log_file:
        config["handlers"]["file"] = {
            "()": RotatingFileHandler,
            "level": level,
            "formatter": "json",
            "filename": log_file,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        }
        config["loggers"][""]["handlers"].append("file")
        config["loggers"]["botspool_shared_utils"]["handlers"].append("file")

    logging.config.dictConfig(config)


def configure_production_logging(
    level: str = "INFO", log_file: Optional[str] = None, log_dir: Optional[str] = None
) -> None:
    """
    Configure logging for production environment.

    Args:
        level: Log level
        log_file: Log file path
        log_dir: Log directory path
    """
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "json",
                "stream": sys.stdout,
            }
        },
        "loggers": {
            "": {"level": level, "handlers": ["console"], "propagate": False},
            "botspool_shared_utils": {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    # Add file handler if specified
    if log_file:
        config["handlers"]["file"] = {
            "()": RotatingFileHandler,
            "level": level,
            "formatter": "json",
            "filename": log_file,
            "maxBytes": 104857600,  # 100MB
            "backupCount": 10,
        }
        config["loggers"][""]["handlers"].append("file")
        config["loggers"]["botspool_shared_utils"]["handlers"].append("file")

    # Add separate error log file
    if log_dir:
        error_log_file = os.path.join(log_dir, "error.log")
        config["handlers"]["error_file"] = {
            "()": RotatingFileHandler,
            "level": "ERROR",
            "formatter": "json",
            "filename": error_log_file,
            "maxBytes": 104857600,  # 100MB
            "backupCount": 10,
        }
        config["loggers"][""]["handlers"].append("error_file")
        config["loggers"]["botspool_shared_utils"]["handlers"].append("error_file")

    logging.config.dictConfig(config)


def configure_test_logging(level: str = "WARNING") -> None:
    """
    Configure logging for test environment.

    Args:
        level: Log level
    """
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"simple": {"format": "%(levelname)s | %(name)s | %(message)s"}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "simple",
                "stream": sys.stdout,
            }
        },
        "loggers": {
            "": {"level": level, "handlers": ["console"], "propagate": False},
            "botspool_shared_utils": {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


def set_log_level(level: str) -> None:
    """
    Set the log level for all loggers.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.getLogger().setLevel(getattr(logging, level.upper()))


def add_log_handler(handler: logging.Handler) -> None:
    """
    Add a log handler to the root logger.

    Args:
        handler: Log handler to add
    """
    logging.getLogger().addHandler(handler)


def remove_log_handler(handler: logging.Handler) -> None:
    """
    Remove a log handler from the root logger.

    Args:
        handler: Log handler to remove
    """
    logging.getLogger().removeHandler(handler)
