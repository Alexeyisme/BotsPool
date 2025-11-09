"""
Retry Strategy Implementation

This module provides retry mechanisms with exponential backoff for handling
transient failures in distributed systems.
"""

import asyncio
import random
import time
from typing import Callable, Any, Optional, List, Type, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from .errors import (
    ExternalServiceError,
    DatabaseError,
    GraphServiceError,
    ErrorCode,
    ErrorCategory,
    ErrorSeverity,
)
from .models.enums import ErrorSeverity as ErrorSeverityEnum

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types."""

    FIXED = "fixed"
    """Fixed delay between retries."""

    EXPONENTIAL = "exponential"
    """Exponential backoff with jitter."""

    LINEAR = "linear"
    """Linear increase in delay."""

    CUSTOM = "custom"
    """Custom retry logic."""


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    """Maximum number of retry attempts."""

    base_delay: float = 1.0
    """Base delay in seconds for the first retry."""

    max_delay: float = 60.0
    """Maximum delay between retries in seconds."""

    exponential_base: float = 2.0
    """Base for exponential backoff calculation."""

    jitter: bool = True
    """Whether to add random jitter to delays."""

    jitter_range: float = 0.1
    """Range of jitter as a fraction of delay (0.1 = ±10%)."""

    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    """Retry strategy to use."""

    retryable_exceptions: Tuple[Type[Exception], ...] = (
        ExternalServiceError,
        DatabaseError,
        GraphServiceError,
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )
    """Exception types that should trigger retries."""

    non_retryable_exceptions: Tuple[Type[Exception], ...] = (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
    )
    """Exception types that should not trigger retries."""

    timeout: Optional[float] = None
    """Timeout for individual retry attempts."""

    backoff_multiplier: float = 1.0
    """Multiplier for backoff calculation."""

    name: str = "retry_manager"
    """Name for logging and monitoring."""


@dataclass
class RetryStats:
    """Statistics for retry operations."""

    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    retry_count: int = 0
    total_delay: float = 0.0
    last_attempt_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None


class RetryExhaustedError(Exception):
    """Exception raised when all retry attempts are exhausted."""

    def __init__(self, message: str, last_exception: Exception, attempts: int):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts


class RetryManager:
    """
    Retry manager with configurable retry strategies.

    Supports multiple retry strategies including fixed delay, exponential backoff,
    and linear backoff with optional jitter.
    """

    def __init__(self, config: RetryConfig):
        self.config = config
        self.stats = RetryStats()

        logger.info(f"Retry manager '{config.name}' initialized with config: {config}")

    async def retry_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Retry an async function with the configured retry strategy.

        Args:
            func: Async function to retry
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            RetryExhaustedError: If all retry attempts are exhausted
            Exception: Last exception if retries are exhausted
        """
        last_exception = None
        attempt = 0

        while attempt < self.config.max_attempts:
            attempt += 1
            self.stats.total_attempts += 1
            self.stats.last_attempt_time = time.time()

            try:
                # Execute function with optional timeout
                if self.config.timeout:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs), timeout=self.config.timeout
                    )
                else:
                    result = await func(*args, **kwargs)

                # Success
                self.stats.successful_attempts += 1
                self.stats.last_success_time = time.time()

                if attempt > 1:
                    self.stats.retry_count += 1
                    logger.info(
                        f"Retry manager '{self.config.name}' succeeded on attempt {attempt}"
                    )

                return result

            except Exception as e:
                last_exception = e
                self.stats.failed_attempts += 1
                self.stats.last_failure_time = time.time()

                # Check if exception is retryable
                if not self._is_retryable_exception(e):
                    logger.warning(
                        f"Retry manager '{self.config.name}' encountered non-retryable exception: {e}"
                    )
                    raise e

                # Check if this was the last attempt
                if attempt >= self.config.max_attempts:
                    logger.error(
                        f"Retry manager '{self.config.name}' exhausted all {self.config.max_attempts} attempts"
                    )
                    raise RetryExhaustedError(
                        f"All {self.config.max_attempts} retry attempts exhausted",
                        last_exception,
                        attempt,
                    )

                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt)
                self.stats.total_delay += delay

                logger.warning(
                    f"Retry manager '{self.config.name}' attempt {attempt} failed: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )

                # Wait before next attempt
                await asyncio.sleep(delay)

    def retry_sync(self, func: Callable, *args, **kwargs) -> Any:
        """
        Retry a sync function with the configured retry strategy.

        Args:
            func: Sync function to retry
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            RetryExhaustedError: If all retry attempts are exhausted
            Exception: Last exception if retries are exhausted
        """
        last_exception = None
        attempt = 0

        while attempt < self.config.max_attempts:
            attempt += 1
            self.stats.total_attempts += 1
            self.stats.last_attempt_time = time.time()

            try:
                # Execute function with optional timeout
                if self.config.timeout:
                    result = asyncio.run(
                        asyncio.wait_for(
                            asyncio.to_thread(func, *args, **kwargs),
                            timeout=self.config.timeout,
                        )
                    )
                else:
                    result = func(*args, **kwargs)

                # Success
                self.stats.successful_attempts += 1
                self.stats.last_success_time = time.time()

                if attempt > 1:
                    self.stats.retry_count += 1
                    logger.info(
                        f"Retry manager '{self.config.name}' succeeded on attempt {attempt}"
                    )

                return result

            except Exception as e:
                last_exception = e
                self.stats.failed_attempts += 1
                self.stats.last_failure_time = time.time()

                # Check if exception is retryable
                if not self._is_retryable_exception(e):
                    logger.warning(
                        f"Retry manager '{self.config.name}' encountered non-retryable exception: {e}"
                    )
                    raise e

                # Check if this was the last attempt
                if attempt >= self.config.max_attempts:
                    logger.error(
                        f"Retry manager '{self.config.name}' exhausted all {self.config.max_attempts} attempts"
                    )
                    raise RetryExhaustedError(
                        f"All {self.config.max_attempts} retry attempts exhausted",
                        last_exception,
                        attempt,
                    )

                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt)
                self.stats.total_delay += delay

                logger.warning(
                    f"Retry manager '{self.config.name}' attempt {attempt} failed: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )

                # Wait before next attempt
                time.sleep(delay)

    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if an exception is retryable."""
        # Check if exception is in non-retryable list
        if isinstance(exception, self.config.non_retryable_exceptions):
            return False

        # Check if exception is in retryable list
        if isinstance(exception, self.config.retryable_exceptions):
            return True

        # Check if exception has retryable attribute
        if hasattr(exception, "retryable"):
            return exception.retryable

        # Default to retryable for unknown exceptions
        return True

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay

        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = min(
                self.config.base_delay
                * (self.config.exponential_base ** (attempt - 1)),
                self.config.max_delay,
            )

        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = min(
                self.config.base_delay * attempt * self.config.backoff_multiplier,
                self.config.max_delay,
            )

        else:
            # Default to exponential
            delay = min(
                self.config.base_delay
                * (self.config.exponential_base ** (attempt - 1)),
                self.config.max_delay,
            )

        # Apply jitter if enabled
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_range
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter)

        return delay

    def get_stats(self) -> RetryStats:
        """Get current retry statistics."""
        return self.stats

    def reset_stats(self):
        """Reset retry statistics."""
        self.stats = RetryStats()
        logger.info(f"Retry manager '{self.config.name}' statistics reset")


class RetryManagerRegistry:
    """Registry for managing multiple retry managers."""

    def __init__(self):
        self._managers: dict[str, RetryManager] = {}

    def create_manager(
        self, name: str, config: Optional[RetryConfig] = None
    ) -> RetryManager:
        """Create a new retry manager."""
        if config is None:
            config = RetryConfig(name=name)
        else:
            config.name = name

        if name in self._managers:
            raise ValueError(f"Retry manager '{name}' already exists")

        manager = RetryManager(config)
        self._managers[name] = manager

        logger.info(f"Created retry manager '{name}'")
        return manager

    def get_manager(self, name: str) -> Optional[RetryManager]:
        """Get a retry manager by name."""
        return self._managers.get(name)

    def remove_manager(self, name: str) -> bool:
        """Remove a retry manager."""
        if name in self._managers:
            del self._managers[name]
            logger.info(f"Removed retry manager '{name}'")
            return True
        return False

    def get_all_stats(self) -> dict[str, RetryStats]:
        """Get statistics for all retry managers."""
        return {name: manager.get_stats() for name, manager in self._managers.items()}


# Global retry manager registry
_retry_registry = RetryManagerRegistry()


def get_retry_manager(name: str) -> Optional[RetryManager]:
    """Get a retry manager by name from the global registry."""
    return _retry_registry.get_manager(name)


def create_retry_manager(
    name: str, config: Optional[RetryConfig] = None
) -> RetryManager:
    """Create a new retry manager using the global registry."""
    return _retry_registry.create_manager(name, config)


def get_retry_registry() -> RetryManagerRegistry:
    """Get the global retry manager registry."""
    return _retry_registry


# Decorator for easy retry usage
def retry(name: str, config: Optional[RetryConfig] = None):
    """
    Decorator to add retry functionality to a function.

    Args:
        name: Name for the retry manager
        config: Retry configuration

    Example:
        @retry("external_api", RetryConfig(max_attempts=5, base_delay=2.0))
        async def call_external_api():
            # Function implementation
            pass
    """

    def decorator(func: Callable) -> Callable:
        manager = create_retry_manager(name, config)

        async def async_wrapper(*args, **kwargs):
            return await manager.retry_async(func, *args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            return manager.retry_sync(func, *args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Convenience functions for common retry scenarios
def retry_external_service(
    max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 30.0
) -> RetryConfig:
    """Create retry config for external service calls."""
    return RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=RetryStrategy.EXPONENTIAL,
        retryable_exceptions=(
            ExternalServiceError,
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        ),
    )


def retry_database_operation(
    max_attempts: int = 3, base_delay: float = 0.5, max_delay: float = 10.0
) -> RetryConfig:
    """Create retry config for database operations."""
    return RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=RetryStrategy.EXPONENTIAL,
        retryable_exceptions=(DatabaseError, ConnectionError, TimeoutError),
    )


def retry_graph_service(
    max_attempts: int = 2, base_delay: float = 2.0, max_delay: float = 60.0
) -> RetryConfig:
    """Create retry config for graph service calls."""
    return RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=RetryStrategy.EXPONENTIAL,
        retryable_exceptions=(
            GraphServiceError,
            ExternalServiceError,
            TimeoutError,
            asyncio.TimeoutError,
        ),
    )
