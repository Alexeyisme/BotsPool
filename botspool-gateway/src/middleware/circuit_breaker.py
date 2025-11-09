"""
Circuit breaker middleware for BotsPool Gateway

This middleware integrates with botspool-shared-utils circuit breaker
to provide fault tolerance for external service calls.
"""

import logging
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from botspool_shared_utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerManager,
    get_circuit_breaker_manager,
)
from botspool_shared_utils.errors import ExternalServiceError, ErrorCode

logger = logging.getLogger(__name__)


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """
    Circuit breaker middleware for protecting against cascading failures.

    This middleware wraps external service calls with circuit breakers
    to prevent system overload when external services are failing.
    """

    def __init__(
        self,
        app,
        circuit_manager: Optional[CircuitBreakerManager] = None,
        default_config: Optional[CircuitBreakerConfig] = None,
    ):
        super().__init__(app)

        self.circuit_manager = circuit_manager or get_circuit_breaker_manager()
        self.default_config = default_config or CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=3,
            timeout=30.0,
            name="gateway_default",
        )

        # Create default circuit breaker
        self.default_circuit = self.circuit_manager.create_circuit(
            "gateway_default", self.default_config
        )

        logger.info("Circuit breaker middleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through circuit breaker.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response: HTTP response

        Raises:
            ExternalServiceError: If circuit breaker is open
        """
        # Determine circuit breaker to use based on path
        circuit_name = self._get_circuit_name(request)
        circuit = self._get_or_create_circuit(circuit_name)

        try:
            # Execute request through circuit breaker
            response = await circuit.call(call_next, request)
            return response

        except ExternalServiceError as exc:
            # Circuit breaker is open or service failed
            logger.warning(
                f"Circuit breaker '{circuit_name}' blocked request: {request.method} {request.url.path}",
                extra={
                    "circuit_name": circuit_name,
                    "path": request.url.path,
                    "method": request.method,
                    "error_code": exc.error_code.value,
                },
            )

            # Re-raise the circuit breaker error
            raise

    def _get_circuit_name(self, request: Request) -> str:
        """
        Determine circuit breaker name based on request path.

        Args:
            request: FastAPI request

        Returns:
            str: Circuit breaker name
        """
        path = request.url.path

        # Map specific paths to circuit breakers
        if path.startswith("/api/v1/chat/"):
            # Extract graph type for more specific circuit breakers
            path_parts = path.split("/")
            if len(path_parts) >= 4:
                graph_type = path_parts[3]
                return f"chat_{graph_type}"
            return "chat_service"
        elif path.startswith("/api/v1/graphs/"):
            return "graph_service"
        elif path.startswith("/api/v1/auth/"):
            return "auth_service"
        elif path.startswith("/health") or path.startswith("/status"):
            return "health_check"
        else:
            return "gateway_default"

    def _get_or_create_circuit(self, circuit_name: str) -> CircuitBreaker:
        """
        Get or create circuit breaker for the given name.

        Args:
            circuit_name: Name of the circuit breaker

        Returns:
            CircuitBreaker: Circuit breaker instance
        """
        circuit = self.circuit_manager.get_circuit(circuit_name)

        if circuit is None:
            # Create new circuit breaker with default config
            config = CircuitBreakerConfig(
                name=circuit_name,
                failure_threshold=self.default_config.failure_threshold,
                recovery_timeout=self.default_config.recovery_timeout,
                success_threshold=self.default_config.success_threshold,
                timeout=self.default_config.timeout,
            )
            circuit = self.circuit_manager.create_circuit(circuit_name, config)
            logger.info(f"Created new circuit breaker: {circuit_name}")

        return circuit

    def get_circuit_stats(self) -> dict:
        """
        Get statistics for all circuit breakers.

        Returns:
            dict: Circuit breaker statistics
        """
        return self.circuit_manager.get_all_stats()

    def reset_all_circuits(self):
        """Reset all circuit breakers to closed state."""
        self.circuit_manager.reset_all()
        logger.info("All circuit breakers reset")


# Convenience function for creating middleware
def create_circuit_breaker_middleware(
    circuit_manager: Optional[CircuitBreakerManager] = None,
    default_config: Optional[CircuitBreakerConfig] = None,
) -> CircuitBreakerMiddleware:
    """
    Create circuit breaker middleware with custom configuration.

    Args:
        circuit_manager: Custom circuit breaker manager
        default_config: Default circuit breaker configuration

    Returns:
        CircuitBreakerMiddleware: Configured middleware
    """

    def middleware_factory(app):
        return CircuitBreakerMiddleware(app, circuit_manager, default_config)

    return middleware_factory
