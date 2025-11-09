"""
Graph Registry for BotsPool Gateway

This module provides graph instance registration and service discovery
using Redis for distributed coordination.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from botspool_shared_utils.redis_utils import RedisManager
from botspool_shared_utils.models.enums import GraphType
from botspool_shared_utils.errors import ExternalServiceError, ErrorCode

logger = logging.getLogger(__name__)


@dataclass
class GraphInstance:
    """Graph instance information."""

    instance_id: str
    graph_type: GraphType
    endpoint: str
    status: str = "healthy"
    capacity: int = 100
    current_load: int = 0
    version: str = "1.0.0"
    last_heartbeat: datetime = None
    created_at: datetime = None

    def __post_init__(self):
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.utcnow()
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        data = asdict(self)
        data["last_heartbeat"] = self.last_heartbeat.isoformat()
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphInstance":
        """Create from dictionary."""
        # Normalize types from stored JSON
        data["last_heartbeat"] = datetime.fromisoformat(data["last_heartbeat"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        # Ensure enum type for graph_type
        if isinstance(data.get("graph_type"), str):
            data["graph_type"] = GraphType(data["graph_type"])
        return cls(**data)


class GraphRegistry:
    """
    Graph instance registry for service discovery.

    Manages graph instances using Redis for distributed coordination.
    Provides registration, discovery, and health monitoring.
    """

    def __init__(
        self,
        redis_manager: RedisManager,
        heartbeat_interval: int = 60,
        stale_threshold: int = 180,
    ):
        # Accept either a RedisManager (from shared-utils) or a raw redis client
        # Normalize to a redis client with set/sadd/get/delete APIs
        self.redis = getattr(redis_manager, "redis_client", redis_manager)
        self.heartbeat_interval = heartbeat_interval
        self.stale_threshold = stale_threshold
        self.logger = logging.getLogger(__name__)

        # Redis key patterns
        self.instance_key_pattern = "graph:instance:{instance_id}"
        self.graph_instances_key_pattern = "graph:instances:{graph_type}"
        self.all_instances_key = "graph:instances:all"

    async def register_instance(
        self,
        instance_id: str,
        graph_type: GraphType,
        endpoint: str,
        capacity: int = 100,
        version: str = "1.0.0",
    ) -> bool:
        """
        Register a new graph instance.

        Args:
            instance_id: Unique instance identifier
            graph_type: Type of graph (todo, email, calendar, etc.)
            endpoint: Instance endpoint URL
            capacity: Maximum concurrent requests
            version: Instance version

        Returns:
            bool: True if registration successful
        """
        try:
            # Create instance record
            instance = GraphInstance(
                instance_id=instance_id,
                graph_type=graph_type,
                endpoint=endpoint,
                capacity=capacity,
                version=version,
            )

            # Store instance data
            instance_key = self.instance_key_pattern.format(instance_id=instance_id)
            await self.redis.set(
                instance_key,
                json.dumps(instance.to_dict()),
                ex=self.heartbeat_interval * 3,  # 3x heartbeat interval
            )

            # Add to graph type set
            graph_instances_key = self.graph_instances_key_pattern.format(
                graph_type=graph_type.value
            )
            await self.redis.sadd(graph_instances_key, instance_id)

            # Add to all instances set
            await self.redis.sadd(self.all_instances_key, instance_id)

            self.logger.info(
                f"Registered graph instance: {instance_id} ({graph_type.value})"
            )
            return True

        except Exception as exc:
            self.logger.error(f"Failed to register instance {instance_id}: {exc}")
            return False

    async def unregister_instance(self, instance_id: str) -> bool:
        """
        Unregister a graph instance.

        Args:
            instance_id: Instance identifier

        Returns:
            bool: True if unregistration successful
        """
        try:
            # Get instance data first
            instance = await self.get_instance(instance_id)
            if not instance:
                return False

            # Remove from all sets
            graph_instances_key = self.graph_instances_key_pattern.format(
                graph_type=instance.graph_type.value
            )
            await self.redis.srem(graph_instances_key, instance_id)
            await self.redis.srem(self.all_instances_key, instance_id)

            # Delete instance data
            instance_key = self.instance_key_pattern.format(instance_id=instance_id)
            await self.redis.delete(instance_key)

            self.logger.info(f"Unregistered graph instance: {instance_id}")
            return True

        except Exception as exc:
            self.logger.error(f"Failed to unregister instance {instance_id}: {exc}")
            return False

    async def update_heartbeat(self, instance_id: str) -> bool:
        """
        Update instance heartbeat.

        Args:
            instance_id: Instance identifier

        Returns:
            bool: True if heartbeat updated
        """
        try:
            instance = await self.get_instance(instance_id)
            if not instance:
                return False

            # Update heartbeat timestamp
            instance.last_heartbeat = datetime.utcnow()

            # Update in Redis
            instance_key = self.instance_key_pattern.format(instance_id=instance_id)
            await self.redis.set(
                instance_key,
                json.dumps(instance.to_dict()),
                ex=self.heartbeat_interval * 3,
            )

            return True

        except Exception as exc:
            self.logger.error(f"Failed to update heartbeat for {instance_id}: {exc}")
            return False

    async def get_instance(self, instance_id: str) -> Optional[GraphInstance]:
        """
        Get instance by ID.

        Args:
            instance_id: Instance identifier

        Returns:
            Optional[GraphInstance]: Instance data or None
        """
        try:
            instance_key = self.instance_key_pattern.format(instance_id=instance_id)
            data = await self.redis.get(instance_key)

            if not data:
                return None

            return GraphInstance.from_dict(json.loads(data))

        except Exception as exc:
            self.logger.error(f"Failed to get instance {instance_id}: {exc}")
            return None

    async def get_instances_by_type(self, graph_type: GraphType) -> List[GraphInstance]:
        """
        Get all instances of a specific graph type.

        Args:
            graph_type: Graph type to filter by

        Returns:
            List[GraphInstance]: List of instances
        """
        try:
            graph_instances_key = self.graph_instances_key_pattern.format(
                graph_type=graph_type.value
            )
            instance_ids = await self.redis.smembers(graph_instances_key)

            instances = []
            for instance_id in instance_ids:
                instance = await self.get_instance(instance_id)
                if instance and self._is_instance_healthy(instance):
                    instances.append(instance)

            return instances

        except Exception as exc:
            self.logger.error(f"Failed to get instances for {graph_type.value}: {exc}")
            return []

    async def get_all_instances(self) -> List[GraphInstance]:
        """
        Get all registered instances.

        Returns:
            List[GraphInstance]: List of all instances
        """
        try:
            instance_ids = await self.redis.smembers(self.all_instances_key)

            instances = []
            for instance_id in instance_ids:
                instance = await self.get_instance(instance_id)
                if instance:
                    instances.append(instance)

            return instances

        except Exception as exc:
            self.logger.error(f"Failed to get all instances: {exc}")
            return []

    async def get_healthy_instances(self, graph_type: GraphType) -> List[GraphInstance]:
        """
        Get healthy instances of a specific graph type.

        Args:
            graph_type: Graph type to filter by

        Returns:
            List[GraphInstance]: List of healthy instances
        """
        instances = await self.get_instances_by_type(graph_type)
        return [inst for inst in instances if self._is_instance_healthy(inst)]

    async def cleanup_stale_instances(self) -> int:
        """
        Clean up stale instances.

        Returns:
            int: Number of instances cleaned up
        """
        try:
            all_instances = await self.get_all_instances()
            cleaned_count = 0

            for instance in all_instances:
                if self._is_instance_stale(instance):
                    await self.unregister_instance(instance.instance_id)
                    cleaned_count += 1
                    self.logger.info(
                        f"Cleaned up stale instance: {instance.instance_id}"
                    )

            return cleaned_count

        except Exception as exc:
            self.logger.error(f"Failed to cleanup stale instances: {exc}")
            return 0

    def _is_instance_healthy(self, instance: GraphInstance) -> bool:
        """
        Check if instance is healthy.

        Args:
            instance: Graph instance

        Returns:
            bool: True if healthy
        """
        if instance.status != "healthy":
            return False

        # Check if heartbeat is recent
        time_since_heartbeat = datetime.utcnow() - instance.last_heartbeat
        return time_since_heartbeat.total_seconds() < self.stale_threshold

    def _is_instance_stale(self, instance: GraphInstance) -> bool:
        """
        Check if instance is stale.

        Args:
            instance: Graph instance

        Returns:
            bool: True if stale
        """
        time_since_heartbeat = datetime.utcnow() - instance.last_heartbeat
        return time_since_heartbeat.total_seconds() > self.stale_threshold

    async def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dict[str, Any]: Registry statistics
        """
        try:
            all_instances = await self.get_all_instances()

            stats = {
                "total_instances": len(all_instances),
                "healthy_instances": 0,
                "unhealthy_instances": 0,
                "by_graph_type": {},
                "by_status": {},
            }

            for instance in all_instances:
                # Count by health
                if self._is_instance_healthy(instance):
                    stats["healthy_instances"] += 1
                else:
                    stats["unhealthy_instances"] += 1

                # Count by graph type
                graph_type = instance.graph_type.value
                if graph_type not in stats["by_graph_type"]:
                    stats["by_graph_type"][graph_type] = 0
                stats["by_graph_type"][graph_type] += 1

                # Count by status
                status = instance.status
                if status not in stats["by_status"]:
                    stats["by_status"][status] = 0
                stats["by_status"][status] += 1

            return stats

        except Exception as exc:
            self.logger.error(f"Failed to get registry stats: {exc}")
            return {"error": str(exc)}


# Global registry instance
_registry: Optional[GraphRegistry] = None


def get_graph_registry() -> GraphRegistry:
    """
    Get the global graph registry instance.

    Returns:
        GraphRegistry: Registry instance
    """
    global _registry

    if _registry is None:
        # Lazy initialize using settings to keep call sites simple
        try:
            from ..config import get_settings
            import redis.asyncio as redis

            settings = get_settings()
            redis_client = redis.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                decode_responses=settings.redis_decode_responses,
                encoding="utf-8",
            )
            redis_manager = RedisManager(redis_client)
            return create_graph_registry(redis_manager)
        except Exception as exc:
            raise RuntimeError(f"Graph registry not initialized: {exc}")

    return _registry


def create_graph_registry(
    redis_manager: RedisManager,
    heartbeat_interval: int = 60,
    stale_threshold: int = 180,
) -> GraphRegistry:
    """
    Create a new graph registry instance.

    Args:
        redis_manager: Redis manager instance
        heartbeat_interval: Heartbeat interval in seconds
        stale_threshold: Stale threshold in seconds

    Returns:
        GraphRegistry: Registry instance
    """
    global _registry

    _registry = GraphRegistry(
        redis_manager=redis_manager,
        heartbeat_interval=heartbeat_interval,
        stale_threshold=stale_threshold,
    )

    return _registry
