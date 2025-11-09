"""
Graph Router for BotsPool Gateway

This module provides request routing functionality for directing
chat requests to appropriate graph instances with failover support.
"""

import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from botspool_shared_utils.models.enums import GraphType, FrontendType
from botspool_shared_utils.errors import (
    ExternalServiceError,
    ValidationError,
    AuthorizationError,
    ErrorCode,
)
from botspool_shared_utils.auth.rbac import RBACManager, get_rbac_manager
from botspool_shared_utils.validation.validators import validate_length
from botspool_shared_utils.anonymization.detection import detect_pii

from .load_balancer import LoadBalancer, get_load_balancer
from ..graphs.registry import GraphInstance, GraphRegistry, get_graph_registry
from ..middleware.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class GraphRouter:
    """
    Graph router for directing requests to appropriate instances.

    Handles request routing, failover, validation, and monitoring.
    """

    def __init__(
        self,
        load_balancer: LoadBalancer,
        registry: GraphRegistry,
        rbac_manager: RBACManager,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.load_balancer = load_balancer
        self.registry = registry
        self.rbac_manager = rbac_manager
        self.circuit_breaker = circuit_breaker
        self.logger = logging.getLogger(__name__)

        # Request tracking
        self._active_requests: Dict[str, Dict[str, Any]] = {}

        self.logger.info("Graph router initialized")

    async def route_request(
        self,
        graph_type: GraphType,
        message: str,
        user_id: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        frontend_type: Optional[FrontendType] = None,
    ) -> Dict[str, Any]:
        """
        Route a chat request to the appropriate graph instance.

        Args:
            graph_type: Type of graph to route to
            message: User message
            user_id: User identifier
            session_id: Session identifier
            context: Request context
            metadata: Request metadata
            frontend_type: Frontend type

        Returns:
            Dict[str, Any]: Response from graph instance

        Raises:
            ValidationError: If request validation fails
            AuthorizationError: If user lacks permission
            ExternalServiceError: If routing fails
        """
        request_id = f"req_{int(time.time() * 1000)}"
        start_time = time.time()

        try:
            # Validate request
            await self._validate_request(graph_type, message, user_id)

            # Check user permissions
            await self._check_user_permissions(user_id, graph_type)

            # Detect and handle PII
            sanitized_message = await self._sanitize_message(message)

            # Select instance
            instance = await self._select_instance(graph_type, user_id, session_id)

            # Track active request
            self._active_requests[request_id] = {
                "user_id": user_id,
                "graph_type": graph_type.value,
                "instance_id": instance.instance_id,
                "start_time": start_time,
                "session_id": session_id,
            }

            # Route request to instance
            response = await self._route_to_instance(
                instance,
                graph_type,
                sanitized_message,
                user_id,
                session_id,
                context,
                metadata,
            )

            # Record success
            processing_time = time.time() - start_time
            await self.load_balancer.record_success(instance.instance_id)
            await self.load_balancer.record_response_time(
                instance.instance_id, processing_time
            )

            # Update instance load
            await self.load_balancer.update_instance_load(instance.instance_id, -1)

            # Add routing metadata
            response.update(
                {
                    "request_id": request_id,
                    "instance_id": instance.instance_id,
                    "processing_time": processing_time,
                    "routing_metadata": {
                        "load_balancer_strategy": self.load_balancer.strategy.value,
                        "instance_capacity": instance.capacity,
                        "instance_load": instance.current_load,
                    },
                }
            )

            self.logger.info(
                f"Request {request_id} routed successfully to {instance.instance_id} "
                f"({graph_type.value}) in {processing_time:.3f}s"
            )

            return response

        except Exception as exc:
            # Record failure
            if request_id in self._active_requests:
                instance_id = self._active_requests[request_id].get("instance_id")
                if instance_id:
                    await self.load_balancer.record_failure(instance_id)
                    await self.load_balancer.update_instance_load(instance_id, -1)
                del self._active_requests[request_id]

            self.logger.error(f"Request {request_id} routing failed: {exc}")
            raise

        finally:
            # Clean up active request
            if request_id in self._active_requests:
                del self._active_requests[request_id]

    async def _validate_request(
        self, graph_type: GraphType, message: str, user_id: str
    ) -> None:
        """
        Validate the incoming request.

        Args:
            graph_type: Graph type
            message: User message
            user_id: User identifier

        Raises:
            ValidationError: If validation fails
        """
        # Validate message
        if not message or len(message.strip()) == 0:
            raise ValidationError(
                message="Message cannot be empty",
                error_code=ErrorCode.VALIDATION_INVALID_INPUT_301,
                details={"field": "message", "value": message},
            )

        if len(message) > 10000:  # 10KB limit
            raise ValidationError(
                message="Message too long",
                error_code=ErrorCode.VALIDATION_INVALID_INPUT_301,
                details={
                    "field": "message",
                    "max_length": 10000,
                    "actual_length": len(message),
                },
            )

        # Validate graph type
        if not graph_type:
            raise ValidationError(
                message="Graph type is required",
                error_code=ErrorCode.VALIDATION_INVALID_INPUT_301,
                details={"field": "graph_type"},
            )

        # Validate user ID
        if not user_id or len(user_id.strip()) == 0:
            raise ValidationError(
                message="User ID is required",
                error_code=ErrorCode.VALIDATION_INVALID_INPUT_301,
                details={"field": "user_id"},
            )

    async def _check_user_permissions(
        self, user_id: str, graph_type: GraphType
    ) -> None:
        """
        Check if user has permission to access the graph.

        Note: Permission checking is now handled at the API layer (chat.py)
        before routing requests. This method is kept for backward compatibility
        but no longer performs actual checks.

        Args:
            user_id: User identifier
            graph_type: Graph type

        Raises:
            AuthorizationError: If user lacks permission (not currently used)
        """
        # Permission checks are now handled in chat.py before routing
        # This method is a placeholder for backward compatibility
        pass

    async def _sanitize_message(self, message: str) -> str:
        """
        Sanitize message content.

        Args:
            message: Original message

        Returns:
            str: Sanitized message
        """
        try:
            # Detect PII
            pii_detected = detect_pii(message)

            if pii_detected:
                self.logger.warning(f"PII detected in message: {pii_detected}")
                # In production, you might want to:
                # 1. Anonymize the PII
                # 2. Log the detection
                # 3. Apply privacy policies

            # Basic input validation and sanitization
            if not validate_length(message, max_length=10000):
                raise ValidationError("Message too long", ErrorCode.VALIDATION_ERROR)
            sanitized = message.strip()

            return sanitized

        except Exception as exc:
            self.logger.error(f"Message sanitization failed: {exc}")
            # Return original message if sanitization fails
            return message

    async def _select_instance(
        self, graph_type: GraphType, user_id: str, session_id: Optional[str]
    ) -> GraphInstance:
        """
        Select an appropriate graph instance.

        Args:
            graph_type: Graph type
            user_id: User identifier
            session_id: Session identifier

        Returns:
            GraphInstance: Selected instance

        Raises:
            ExternalServiceError: If no instances available
        """
        try:
            # Use load balancer to select instance
            instance = await self.load_balancer.select_instance(
                graph_type=graph_type, user_id=user_id, session_id=session_id
            )

            if not instance:
                raise ExternalServiceError(
                    message=f"No instances available for {graph_type.value}",
                    service_name=f"graph_{graph_type.value}",
                    error_code=ErrorCode.GRAPH_NO_INSTANCES_AVAILABLE_005,
                    details={"graph_type": graph_type.value},
                )

            # Update instance load
            await self.load_balancer.update_instance_load(instance.instance_id, 1)

            return instance

        except Exception as exc:
            self.logger.error(f"Instance selection failed: {exc}")
            raise

    async def _route_to_instance(
        self,
        instance: GraphInstance,
        graph_type: GraphType,
        message: str,
        user_id: str,
        session_id: Optional[str],
        context: Optional[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Route request to specific instance by forwarding to the instance HTTP API.

        Args:
            instance: Target instance
            graph_type: Graph type
            message: User message
            user_id: User identifier
            session_id: Session identifier
            context: Request context
            metadata: Request metadata

        Returns:
            Dict[str, Any]: Response from instance
        """
        try:
            import httpx

            # Build target URL and payload expected by the ToDo Graph service
            target_url = f"{instance.endpoint.rstrip('/')}/api/v1/chat"
            params = {"user_id": user_id}
            payload: Dict[str, Any] = {
                "message": message,
                "session_id": session_id,
                "context": context or {},
            }

            timeout = httpx.Timeout(30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(target_url, params=params, json=payload)

            if resp.status_code != 200:
                self.logger.error(
                    f"Instance {instance.instance_id} returned {resp.status_code}: {resp.text}"
                )
                raise ExternalServiceError(
                    message=f"Instance {instance.instance_id} error {resp.status_code}",
                    service_name=instance.instance_id,
                    error_code=ErrorCode.GRAPH_INVALID_RESPONSE_004,
                    details={
                        "instance_id": instance.instance_id,
                        "status_code": resp.status_code,
                        "body": resp.text[:500],
                    },
                )

            data = resp.json()

            # Ensure required fields; augment with routing metadata
            if not isinstance(data, dict):
                raise ExternalServiceError(
                    message="Invalid response payload",
                    service_name=instance.instance_id,
                    error_code=ErrorCode.GRAPH_INVALID_RESPONSE_004,
                    details={"instance_id": instance.instance_id},
                )

            data.setdefault("graph_type", graph_type.value)
            data.setdefault("user_id", user_id)
            data.setdefault("session_id", session_id or f"session_{int(time.time())}")
            data.setdefault("timestamp", datetime.utcnow().isoformat())
            data["instance_id"] = instance.instance_id
            data.setdefault("metadata", {})
            data["metadata"].update(
                {
                    "forwarded_via": "gateway",
                    "instance_endpoint": instance.endpoint,
                }
            )

            return data

        except ExternalServiceError:
            raise
        except Exception as exc:
            self.logger.error(
                f"Request routing to {instance.instance_id} failed: {exc}"
            )
            raise ExternalServiceError(
                message=f"Failed to route request to {instance.instance_id}",
                service_name=instance.instance_id,
                error_code=ErrorCode.EXTERNAL_API_ERROR_001,
                details={
                    "instance_id": instance.instance_id,
                    "graph_type": graph_type.value,
                    "error": str(exc),
                },
            )

    async def handle_failover(
        self,
        original_instance: GraphInstance,
        graph_type: GraphType,
        user_id: str,
        session_id: Optional[str],
    ) -> GraphInstance:
        """
        Handle failover to a different instance.

        Args:
            original_instance: Original instance that failed
            graph_type: Graph type
            user_id: User identifier
            session_id: Session identifier

        Returns:
            GraphInstance: Alternative instance

        Raises:
            ExternalServiceError: If no alternative instances available
        """
        try:
            # Get all instances except the failed one
            all_instances = await self.registry.get_healthy_instances(graph_type)
            alternative_instances = [
                inst
                for inst in all_instances
                if inst.instance_id != original_instance.instance_id
            ]

            if not alternative_instances:
                raise ExternalServiceError(
                    message=f"No alternative instances available for {graph_type.value}",
                    service_name=f"graph_{graph_type.value}",
                    error_code=ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE_602,
                    details={
                        "graph_type": graph_type.value,
                        "failed_instance": original_instance.instance_id,
                    },
                )

            # Select alternative instance
            alternative_instance = await self.load_balancer.select_instance(
                graph_type=graph_type, user_id=user_id, session_id=session_id
            )

            self.logger.info(
                f"Failover from {original_instance.instance_id} to {alternative_instance.instance_id}"
            )

            return alternative_instance

        except Exception as exc:
            self.logger.error(f"Failover failed: {exc}")
            raise

    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics.

        Returns:
            Dict[str, Any]: Routing statistics
        """
        return {
            "active_requests": len(self._active_requests),
            "load_balancer_stats": self.load_balancer.get_balancing_stats(),
            "active_request_details": list(self._active_requests.values()),
        }

    def get_active_requests(self) -> List[Dict[str, Any]]:
        """
        Get list of active requests.

        Returns:
            List[Dict[str, Any]]: Active request details
        """
        return list(self._active_requests.values())


# Global router instance
_router: Optional[GraphRouter] = None


def get_graph_router() -> GraphRouter:
    """
    Get the global graph router instance.

    Returns:
        GraphRouter: Router instance

    Raises:
        RuntimeError: If router not initialized
    """
    global _router

    if _router is None:
        raise RuntimeError("Graph router not initialized")

    return _router


def create_graph_router(
    load_balancer: LoadBalancer,
    registry: GraphRegistry,
    rbac_manager: RBACManager,
    circuit_breaker: Optional[CircuitBreaker] = None,
) -> GraphRouter:
    """
    Create a new graph router instance.

    Args:
        load_balancer: Load balancer instance
        registry: Graph registry instance
        rbac_manager: RBAC manager instance
        circuit_breaker: Circuit breaker instance

    Returns:
        GraphRouter: Router instance
    """
    global _router

    _router = GraphRouter(
        load_balancer=load_balancer,
        registry=registry,
        rbac_manager=rbac_manager,
        circuit_breaker=circuit_breaker,
    )

    return _router
