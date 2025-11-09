"""
Circuit Breaker Pattern Implementation

This module provides a circuit breaker implementation for handling external service
failures and preventing cascading failures in distributed systems.
"""

import asyncio
import time
from enum import Enum
from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass, field
import logging

from .errors import ExternalServiceError, ErrorCode, ErrorCategory, ErrorSeverity
from .models.enums import CircuitState

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5
    """Number of consecutive failures before opening the circuit."""

    recovery_timeout: int = 60
    """Time in seconds to wait before attempting to close the circuit."""

    success_threshold: int = 3
    """Number of consecutive successes required to close the circuit."""

    expected_exception: type = Exception
    """Exception type that should trigger the circuit breaker."""

    timeout: float = 30.0
    """Timeout for individual operations in seconds."""

    name: str = "circuit_breaker"
    """Name of the circuit breaker for logging and monitoring."""


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_opened_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    current_state: CircuitState = CircuitState.CLOSED


class CircuitBreakerOpenError(ExternalServiceError):
    """Exception raised when circuit breaker is open."""

    def __init__(self, circuit_name: str, retry_after: float):
        super().__init__(
            message=f"Circuit breaker '{circuit_name}' is open. Service unavailable.",
            error_code=ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE_602,
            details={"circuit_name": circuit_name, "retry_after": retry_after},
            retryable=True,
            retry_after_seconds=int(retry_after),
        )


class CircuitBreaker:
    """
    Circuit breaker implementation for handling external service failures.

    The circuit breaker has three states:
    - CLOSED: Normal operation, requests are allowed
    - OPEN: Circuit is open, requests are rejected immediately
    - HALF_OPEN: Testing if service is back, limited requests allowed
    """

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()
        self.stats = CircuitBreakerStats()

        logger.info(
            f"Circuit breaker '{config.name}' initialized with config: {config}"
        )

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            ExternalServiceError: If function fails and circuit should be opened
        """
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(
                        f"Circuit breaker '{self.config.name}' moved to HALF_OPEN state"
                    )
                else:
                    retry_after = self._get_retry_after()
                    self.stats.circuit_opened_count += 1
                    raise CircuitBreakerOpenError(self.config.name, retry_after)

            self.stats.total_requests += 1

            try:
                # Execute function with timeout
                result = await asyncio.wait_for(
                    self._execute_function(func, *args, **kwargs),
                    timeout=self.config.timeout,
                )

                await self._on_success()
                return result

            except asyncio.TimeoutError:
                await self._on_failure("Operation timed out")
                raise ExternalServiceError(
                    message=f"Operation timed out after {self.config.timeout} seconds",
                    service_name="circuit_breaker",
                    error_code=ErrorCode.EXTERNAL_API_ERROR_001,
                    details={
                        "circuit_name": self.config.name,
                        "timeout": self.config.timeout,
                    },
                )

            except self.config.expected_exception as e:
                await self._on_failure(str(e))
                raise e

            except Exception as e:
                # Unexpected exception, don't count as circuit breaker failure
                logger.error(
                    f"Unexpected error in circuit breaker '{self.config.name}': {e}"
                )
                raise e

    async def _execute_function(self, func: Callable, *args, **kwargs) -> Any:
        """Execute the function, handling both sync and async functions."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, *args, **kwargs)

    async def _on_success(self):
        """Handle successful operation."""
        self.success_count += 1
        self.failure_count = 0
        self.stats.successful_requests += 1
        self.stats.last_success_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                logger.info(
                    f"Circuit breaker '{self.config.name}' moved to CLOSED state"
                )

    async def _on_failure(self, error_message: str):
        """Handle failed operation."""
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = time.time()
        self.stats.failed_requests += 1
        self.stats.last_failure_time = self.last_failure_time

        logger.warning(
            f"Circuit breaker '{self.config.name}' failure {self.failure_count}/{self.config.failure_threshold}: {error_message}"
        )

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit breaker '{self.config.name}' moved to OPEN state")

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True

        return time.time() - self.last_failure_time >= self.config.recovery_timeout

    def _get_retry_after(self) -> float:
        """Get the time to wait before retrying."""
        if self.last_failure_time is None:
            return self.config.recovery_timeout

        elapsed = time.time() - self.last_failure_time
        return max(0, self.config.recovery_timeout - elapsed)

    def get_stats(self) -> CircuitBreakerStats:
        """Get current circuit breaker statistics."""
        self.stats.current_state = self.state
        return self.stats

    def reset(self):
        """Manually reset the circuit breaker to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info(
            f"Circuit breaker '{self.config.name}' manually reset to CLOSED state"
        )


class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""

    def __init__(self):
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    def create_circuit(
        self, name: str, config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Create a new circuit breaker.

        Args:
            name: Unique name for the circuit breaker
            config: Configuration for the circuit breaker

        Returns:
            Created circuit breaker instance

        Raises:
            ValueError: If circuit with name already exists
        """
        if config is None:
            config = CircuitBreakerConfig(name=name)
        else:
            config.name = name

        if name in self._circuits:
            raise ValueError(f"Circuit breaker '{name}' already exists")

        circuit = CircuitBreaker(config)
        self._circuits[name] = circuit

        logger.info(f"Created circuit breaker '{name}'")
        return circuit

    def get_circuit(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        return self._circuits.get(name)

    def remove_circuit(self, name: str) -> bool:
        """Remove a circuit breaker."""
        if name in self._circuits:
            del self._circuits[name]
            logger.info(f"Removed circuit breaker '{name}'")
            return True
        return False

    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers."""
        return {name: circuit.get_stats() for name, circuit in self._circuits.items()}

    def reset_all(self):
        """Reset all circuit breakers to CLOSED state."""
        for circuit in self._circuits.values():
            circuit.reset()
        logger.info("Reset all circuit breakers")


# Global circuit breaker manager instance
_circuit_manager = CircuitBreakerManager()


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager."""
    return _circuit_manager


def create_circuit_breaker(
    name: str, config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Create a new circuit breaker using the global manager."""
    return _circuit_manager.create_circuit(name, config)


def get_circuit_breaker(name: str) -> Optional[CircuitBreaker]:
    """Get a circuit breaker by name from the global manager."""
    return _circuit_manager.get_circuit(name)


# Decorator for easy circuit breaker usage
def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator to add circuit breaker protection to a function.

    Args:
        name: Name for the circuit breaker
        config: Circuit breaker configuration

    Example:
        @circuit_breaker("external_api", CircuitBreakerConfig(failure_threshold=3))
        async def call_external_api():
            # Function implementation
            pass
    """

    def decorator(func: Callable) -> Callable:
        circuit = create_circuit_breaker(name, config)

        async def wrapper(*args, **kwargs):
            return await circuit.call(func, *args, **kwargs)

        return wrapper

    return decorator
