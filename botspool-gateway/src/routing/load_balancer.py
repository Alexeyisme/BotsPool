"""
Load Balancer for BotsPool Gateway

This module provides load balancing functionality for distributing requests
across multiple graph instances using various strategies.
"""

import random
import time
import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from botspool_shared_utils.models.enums import GraphType
from botspool_shared_utils.errors import ExternalServiceError, ErrorCode
from ..graphs.registry import GraphInstance, GraphRegistry

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    HEALTH_BASED = "health_based"
    RANDOM = "random"


@dataclass
class LoadBalancingStats:
    """Load balancing statistics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    requests_by_strategy: Dict[str, int] = field(default_factory=dict)
    requests_by_instance: Dict[str, int] = field(default_factory=dict)
    average_response_time: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)


class LoadBalancer:
    """
    Load balancer for distributing requests across graph instances.

    Supports multiple load balancing strategies and provides
    comprehensive metrics and monitoring.
    """

    def __init__(
        self,
        registry: GraphRegistry,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        health_check_interval: int = 30,
    ):
        self.registry = registry
        self.strategy = strategy
        self.health_check_interval = health_check_interval
        self.logger = logging.getLogger(__name__)

        # Round-robin state
        self._round_robin_counters: Dict[str, int] = {}

        # Connection tracking
        self._active_connections: Dict[str, int] = {}

        # Statistics
        self._stats = LoadBalancingStats()

        # Performance tracking
        self._response_times: Dict[str, List[float]] = {}

        self.logger.info(f"Load balancer initialized with strategy: {strategy.value}")

    async def select_instance(
        self,
        graph_type: GraphType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[GraphInstance]:
        """
        Select a graph instance using the configured strategy.

        Args:
            graph_type: Type of graph to route to
            user_id: User ID for session affinity
            session_id: Session ID for session affinity

        Returns:
            Optional[GraphInstance]: Selected instance or None

        Raises:
            ExternalServiceError: If no healthy instances available
        """
        try:
            # Get healthy instances
            instances = await self.registry.get_healthy_instances(graph_type)

            if not instances:
                self.logger.warning(
                    f"No healthy instances available for {graph_type.value}"
                )
                raise ExternalServiceError(
                    message=f"No healthy instances available for {graph_type.value}",
                    service_name=f"graph_{graph_type.value}",
                    error_code=ErrorCode.GRAPH_NO_INSTANCES_AVAILABLE_005,
                    details={"graph_type": graph_type.value},
                )

            # Select instance based on strategy
            selected_instance = await self._select_by_strategy(
                instances, graph_type, user_id, session_id
            )

            if not selected_instance:
                raise ExternalServiceError(
                    message=f"Failed to select instance for {graph_type.value}",
                    service_name=f"graph_{graph_type.value}",
                    error_code=ErrorCode.GRAPH_LOAD_BALANCE_FAILED_006,
                    details={
                        "graph_type": graph_type.value,
                        "strategy": self.strategy.value,
                    },
                )

            # Update statistics
            self._update_stats(selected_instance)

            self.logger.debug(
                f"Selected instance {selected_instance.instance_id} for {graph_type.value}"
            )

            return selected_instance

        except Exception as exc:
            self.logger.error(f"Instance selection failed: {exc}")
            raise

    async def _select_by_strategy(
        self,
        instances: List[GraphInstance],
        graph_type: GraphType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[GraphInstance]:
        """
        Select instance based on configured strategy.

        Args:
            instances: Available instances
            graph_type: Graph type
            user_id: User ID
            session_id: Session ID

        Returns:
            Optional[GraphInstance]: Selected instance
        """
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return await self._round_robin_selection(instances, graph_type)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return await self._least_connections_selection(instances)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return await self._weighted_round_robin_selection(instances, graph_type)
        elif self.strategy == LoadBalancingStrategy.HEALTH_BASED:
            return await self._health_based_selection(instances)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return await self._random_selection(instances)
        else:
            # Default to round robin
            return await self._round_robin_selection(instances, graph_type)

    async def _round_robin_selection(
        self, instances: List[GraphInstance], graph_type: GraphType
    ) -> Optional[GraphInstance]:
        """Round-robin instance selection."""
        graph_key = graph_type.value

        # Initialize counter if not exists
        if graph_key not in self._round_robin_counters:
            self._round_robin_counters[graph_key] = 0

        # Get next instance in round-robin fashion
        counter = self._round_robin_counters[graph_key]
        selected_instance = instances[counter % len(instances)]

        # Update counter
        self._round_robin_counters[graph_key] = (counter + 1) % len(instances)

        return selected_instance

    async def _least_connections_selection(
        self, instances: List[GraphInstance]
    ) -> Optional[GraphInstance]:
        """Least connections instance selection."""
        # Sort by current load (ascending)
        sorted_instances = sorted(instances, key=lambda x: x.current_load)

        # Return instance with least connections
        return sorted_instances[0] if sorted_instances else None

    async def _weighted_round_robin_selection(
        self, instances: List[GraphInstance], graph_type: GraphType
    ) -> Optional[GraphInstance]:
        """Weighted round-robin instance selection."""
        graph_key = graph_type.value

        # Initialize counter if not exists
        if graph_key not in self._round_robin_counters:
            self._round_robin_counters[graph_key] = 0

        # Calculate weights based on capacity
        total_capacity = sum(instance.capacity for instance in instances)
        if total_capacity == 0:
            return instances[0] if instances else None

        # Weighted selection
        weights = [instance.capacity / total_capacity for instance in instances]
        cumulative_weights = []
        cumulative = 0

        for weight in weights:
            cumulative += weight
            cumulative_weights.append(cumulative)

        # Select based on weighted round-robin
        counter = self._round_robin_counters[graph_key]
        selection = (counter / len(instances)) % 1.0

        for i, cumulative_weight in enumerate(cumulative_weights):
            if selection <= cumulative_weight:
                self._round_robin_counters[graph_key] = (counter + 1) % len(instances)
                return instances[i]

        # Fallback to first instance
        return instances[0] if instances else None

    async def _health_based_selection(
        self, instances: List[GraphInstance]
    ) -> Optional[GraphInstance]:
        """Health-based instance selection."""
        # Filter by health status and sort by load
        healthy_instances = [
            inst
            for inst in instances
            if inst.status == "healthy" and inst.current_load < inst.capacity
        ]

        if not healthy_instances:
            return instances[0] if instances else None

        # Sort by current load (ascending)
        sorted_instances = sorted(healthy_instances, key=lambda x: x.current_load)
        return sorted_instances[0]

    async def _random_selection(
        self, instances: List[GraphInstance]
    ) -> Optional[GraphInstance]:
        """Random instance selection."""
        return random.choice(instances) if instances else None

    async def update_instance_load(self, instance_id: str, load_delta: int) -> bool:
        """
        Update instance load.

        Args:
            instance_id: Instance identifier
            load_delta: Load change (+1 for new request, -1 for completed)

        Returns:
            bool: True if update successful
        """
        try:
            # Update active connections
            current_connections = self._active_connections.get(instance_id, 0)
            new_connections = max(0, current_connections + load_delta)
            self._active_connections[instance_id] = new_connections

            self.logger.debug(
                f"Updated load for {instance_id}: {current_connections} -> {new_connections}"
            )

            return True

        except Exception as exc:
            self.logger.error(f"Failed to update load for {instance_id}: {exc}")
            return False

    def _update_stats(self, instance: GraphInstance):
        """Update load balancing statistics."""
        self._stats.total_requests += 1
        self._stats.requests_by_strategy[self.strategy.value] = (
            self._stats.requests_by_strategy.get(self.strategy.value, 0) + 1
        )
        self._stats.requests_by_instance[instance.instance_id] = (
            self._stats.requests_by_instance.get(instance.instance_id, 0) + 1
        )
        self._stats.last_updated = datetime.utcnow()

    async def record_response_time(self, instance_id: str, response_time: float):
        """
        Record response time for an instance.

        Args:
            instance_id: Instance identifier
            response_time: Response time in seconds
        """
        try:
            if instance_id not in self._response_times:
                self._response_times[instance_id] = []

            # Keep only last 100 response times
            self._response_times[instance_id].append(response_time)
            if len(self._response_times[instance_id]) > 100:
                self._response_times[instance_id] = self._response_times[instance_id][
                    -100:
                ]

            # Update average response time
            all_times = []
            for times in self._response_times.values():
                all_times.extend(times)

            if all_times:
                self._stats.average_response_time = sum(all_times) / len(all_times)

        except Exception as exc:
            self.logger.error(f"Failed to record response time: {exc}")

    async def record_success(self, instance_id: str):
        """Record successful request."""
        self._stats.successful_requests += 1

    async def record_failure(self, instance_id: str):
        """Record failed request."""
        self._stats.failed_requests += 1

    def get_balancing_stats(self) -> LoadBalancingStats:
        """
        Get load balancing statistics.

        Returns:
            LoadBalancingStats: Current statistics
        """
        return self._stats

    def get_instance_stats(self, instance_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific instance.

        Args:
            instance_id: Instance identifier

        Returns:
            Dict[str, Any]: Instance statistics
        """
        response_times = self._response_times.get(instance_id, [])

        return {
            "instance_id": instance_id,
            "active_connections": self._active_connections.get(instance_id, 0),
            "total_requests": self._stats.requests_by_instance.get(instance_id, 0),
            "average_response_time": sum(response_times) / len(response_times)
            if response_times
            else 0.0,
            "response_times_count": len(response_times),
        }

    async def health_check_instances(self) -> Dict[str, Any]:
        """
        Perform health check on all instances.

        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            all_instances = await self.registry.get_all_instances()
            health_results = {
                "total_instances": len(all_instances),
                "healthy_instances": 0,
                "unhealthy_instances": 0,
                "by_graph_type": {},
                "by_status": {},
            }

            for instance in all_instances:
                is_healthy = self.registry._is_instance_healthy(instance)

                if is_healthy:
                    health_results["healthy_instances"] += 1
                else:
                    health_results["unhealthy_instances"] += 1

                # Count by graph type
                graph_type = instance.graph_type.value
                if graph_type not in health_results["by_graph_type"]:
                    health_results["by_graph_type"][graph_type] = {
                        "healthy": 0,
                        "unhealthy": 0,
                    }

                if is_healthy:
                    health_results["by_graph_type"][graph_type]["healthy"] += 1
                else:
                    health_results["by_graph_type"][graph_type]["unhealthy"] += 1

                # Count by status
                status = instance.status
                if status not in health_results["by_status"]:
                    health_results["by_status"][status] = 0
                health_results["by_status"][status] += 1

            return health_results

        except Exception as exc:
            self.logger.error(f"Health check failed: {exc}")
            return {"error": str(exc)}

    def set_strategy(self, strategy: LoadBalancingStrategy):
        """
        Change load balancing strategy.

        Args:
            strategy: New load balancing strategy
        """
        self.strategy = strategy
        self.logger.info(f"Load balancing strategy changed to: {strategy.value}")

    def reset_stats(self):
        """Reset load balancing statistics."""
        self._stats = LoadBalancingStats()
        self._response_times.clear()
        self._active_connections.clear()
        self.logger.info("Load balancing statistics reset")


# Global load balancer instance
_load_balancer: Optional[LoadBalancer] = None


def get_load_balancer() -> LoadBalancer:
    """
    Get the global load balancer instance.

    Returns:
        LoadBalancer: Load balancer instance

    Raises:
        RuntimeError: If load balancer not initialized
    """
    global _load_balancer

    if _load_balancer is None:
        raise RuntimeError("Load balancer not initialized")

    return _load_balancer


def create_load_balancer(
    registry: GraphRegistry,
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
    health_check_interval: int = 30,
) -> LoadBalancer:
    """
    Create a new load balancer instance.

    Args:
        registry: Graph registry instance
        strategy: Load balancing strategy
        health_check_interval: Health check interval in seconds

    Returns:
        LoadBalancer: Load balancer instance
    """
    global _load_balancer

    _load_balancer = LoadBalancer(
        registry=registry,
        strategy=strategy,
        health_check_interval=health_check_interval,
    )

    return _load_balancer
