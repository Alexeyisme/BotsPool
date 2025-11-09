"""
Redis utilities for BotsPool

This module provides Redis key patterns and utilities that align with the
architecture specifications for session management, pool registry, and caching.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID

import redis.asyncio as redis

from .models.enums import FrontendType, GraphType, GraphHealthStatus
from .errors import ConfigurationError, ExternalServiceError

logger = logging.getLogger(__name__)


class RedisKeyPatterns:
    """Redis key patterns as specified in the architecture."""

    # Session management keys
    SESSION = "session:{user_id}"
    USER_SESSIONS = "user_sessions:{user_id}"

    # Pool registry keys
    POOL_INSTANCES = "pool:{graph_type}:instances"
    INSTANCE_INFO = "instance:{instance_id}"
    INSTANCE_HEALTH = "instance:{instance_id}:health"

    # Usage tracking keys
    USAGE_TRACKING = "usage:{user_id}:{date}"
    RATE_LIMIT = "rate_limit:{user_id}:{endpoint}"

    # Cache keys
    USER_CACHE = "user:{user_id}"
    GRAPH_CACHE = "graph:{graph_type}"
    CONFIG_CACHE = "config:{key}"

    # Lock keys
    USER_LOCK = "lock:user:{user_id}"
    GRAPH_LOCK = "lock:graph:{graph_type}"

    @staticmethod
    def format_session_key(user_id: Union[str, UUID]) -> str:
        """Format session key for user."""
        return RedisKeyPatterns.SESSION.format(user_id=str(user_id))

    @staticmethod
    def format_user_sessions_key(user_id: Union[str, UUID]) -> str:
        """Format user sessions key."""
        return RedisKeyPatterns.USER_SESSIONS.format(user_id=str(user_id))

    @staticmethod
    def format_pool_instances_key(graph_type: GraphType) -> str:
        """Format pool instances key for graph type."""
        return RedisKeyPatterns.POOL_INSTANCES.format(graph_type=graph_type.value)

    @staticmethod
    def format_instance_info_key(instance_id: str) -> str:
        """Format instance info key."""
        return RedisKeyPatterns.INSTANCE_INFO.format(instance_id=instance_id)

    @staticmethod
    def format_instance_health_key(instance_id: str) -> str:
        """Format instance health key."""
        return RedisKeyPatterns.INSTANCE_HEALTH.format(instance_id=instance_id)

    @staticmethod
    def format_usage_tracking_key(user_id: Union[str, UUID], date: str) -> str:
        """Format usage tracking key."""
        return RedisKeyPatterns.USAGE_TRACKING.format(user_id=str(user_id), date=date)

    @staticmethod
    def format_rate_limit_key(user_id: Union[str, UUID], endpoint: str) -> str:
        """Format rate limit key."""
        return RedisKeyPatterns.RATE_LIMIT.format(
            user_id=str(user_id), endpoint=endpoint
        )

    @staticmethod
    def format_user_cache_key(user_id: Union[str, UUID]) -> str:
        """Format user cache key."""
        return RedisKeyPatterns.USER_CACHE.format(user_id=str(user_id))

    @staticmethod
    def format_graph_cache_key(graph_type: GraphType) -> str:
        """Format graph cache key."""
        return RedisKeyPatterns.GRAPH_CACHE.format(graph_type=graph_type.value)

    @staticmethod
    def format_config_cache_key(key: str) -> str:
        """Format config cache key."""
        return RedisKeyPatterns.CONFIG_CACHE.format(key=key)

    @staticmethod
    def format_user_lock_key(user_id: Union[str, UUID]) -> str:
        """Format user lock key."""
        return RedisKeyPatterns.USER_LOCK.format(user_id=str(user_id))

    @staticmethod
    def format_graph_lock_key(graph_type: GraphType) -> str:
        """Format graph lock key."""
        return RedisKeyPatterns.GRAPH_LOCK.format(graph_type=graph_type.value)


class SessionData:
    """Session data structure as specified in architecture."""

    def __init__(
        self,
        user_id: Union[str, UUID],
        frontend_type: FrontendType,
        current_graph: Optional[GraphType] = None,
        session_data: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ):
        self.user_id = str(user_id)
        self.frontend_type = frontend_type
        self.current_graph = current_graph
        self.session_data = session_data or {}
        self.expires_at = expires_at or datetime.utcnow() + timedelta(hours=24)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return {
            "user_id": self.user_id,
            "frontend_type": self.frontend_type.value,
            "current_graph": self.current_graph.value if self.current_graph else None,
            "session_data": self.session_data,
            "expires_at": self.expires_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionData":
        """Create from dictionary from Redis storage."""
        return cls(
            user_id=data["user_id"],
            frontend_type=FrontendType(data["frontend_type"]),
            current_graph=GraphType(data["current_graph"])
            if data.get("current_graph")
            else None,
            session_data=data.get("session_data", {}),
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
        )


class InstanceData:
    """Instance data structure as specified in architecture."""

    def __init__(
        self,
        instance_id: str,
        graph_type: GraphType,
        endpoint: str,
        status: GraphHealthStatus = GraphHealthStatus.HEALTHY,
        load: float = 0.0,
        last_heartbeat: Optional[datetime] = None,
    ):
        self.instance_id = instance_id
        self.graph_type = graph_type
        self.endpoint = endpoint
        self.status = status
        self.load = load
        self.last_heartbeat = last_heartbeat or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return {
            "graph_type": self.graph_type.value,
            "endpoint": self.endpoint,
            "status": self.status.value,
            "load": self.load,
            "last_heartbeat": self.last_heartbeat.isoformat(),
        }

    @classmethod
    def from_dict(cls, instance_id: str, data: Dict[str, Any]) -> "InstanceData":
        """Create from dictionary from Redis storage."""
        return cls(
            instance_id=instance_id,
            graph_type=GraphType(data["graph_type"]),
            endpoint=data["endpoint"],
            status=GraphHealthStatus(data["status"]),
            load=data.get("load", 0.0),
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"])
            if data.get("last_heartbeat")
            else None,
        )


class RedisManager:
    """Redis manager with architecture-compliant key patterns."""

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)

    # Session Management
    async def create_session(
        self,
        user_id: Union[str, UUID],
        frontend_type: FrontendType,
        current_graph: Optional[GraphType] = None,
        session_data: Optional[Dict[str, Any]] = None,
        ttl: int = 86400,  # 24 hours
    ) -> SessionData:
        """Create a new user session."""
        session = SessionData(
            user_id=user_id,
            frontend_type=frontend_type,
            current_graph=current_graph,
            session_data=session_data,
        )

        session_key = RedisKeyPatterns.format_session_key(user_id)
        user_sessions_key = RedisKeyPatterns.format_user_sessions_key(user_id)

        # Store session data
        await self.redis_client.setex(session_key, ttl, json.dumps(session.to_dict()))

        # Add to user sessions set
        await self.redis_client.sadd(user_sessions_key, session_key)
        await self.redis_client.expire(user_sessions_key, ttl)

        self.logger.info(f"Created session for user {user_id}")
        return session

    async def get_session(self, user_id: Union[str, UUID]) -> Optional[SessionData]:
        """Get user session data."""
        session_key = RedisKeyPatterns.format_session_key(user_id)
        session_data = await self.redis_client.get(session_key)

        if not session_data:
            return None

        try:
            data = json.loads(session_data)
            return SessionData.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Failed to parse session data for user {user_id}: {e}")
            return None

    async def update_session(
        self,
        user_id: Union[str, UUID],
        current_graph: Optional[GraphType] = None,
        session_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update user session data."""
        session = await self.get_session(user_id)
        if not session:
            return False

        if current_graph is not None:
            session.current_graph = current_graph

        if session_data is not None:
            session.session_data.update(session_data)

        session_key = RedisKeyPatterns.format_session_key(user_id)
        await self.redis_client.setex(
            session_key, 86400, json.dumps(session.to_dict())  # 24 hours
        )

        return True

    async def delete_session(self, user_id: Union[str, UUID]) -> bool:
        """Delete user session."""
        session_key = RedisKeyPatterns.format_session_key(user_id)
        user_sessions_key = RedisKeyPatterns.format_user_sessions_key(user_id)

        # Remove from user sessions set
        await self.redis_client.srem(user_sessions_key, session_key)

        # Delete session data
        deleted = await self.redis_client.delete(session_key)

        if deleted:
            self.logger.info(f"Deleted session for user {user_id}")

        return bool(deleted)

    # Pool Registry Management
    async def register_instance(
        self,
        instance_id: str,
        graph_type: GraphType,
        endpoint: str,
        status: GraphHealthStatus = GraphHealthStatus.HEALTHY,
        load: float = 0.0,
    ) -> InstanceData:
        """Register a new graph instance."""
        instance = InstanceData(
            instance_id=instance_id,
            graph_type=graph_type,
            endpoint=endpoint,
            status=status,
            load=load,
        )

        # Store instance info
        instance_key = RedisKeyPatterns.format_instance_info_key(instance_id)
        await self.redis_client.setex(
            instance_key, 300, json.dumps(instance.to_dict())  # 5 minutes TTL
        )

        # Add to pool instances set
        pool_key = RedisKeyPatterns.format_pool_instances_key(graph_type)
        await self.redis_client.sadd(pool_key, instance_id)

        self.logger.info(
            f"Registered instance {instance_id} for graph {graph_type.value}"
        )
        return instance

    async def get_instance(self, instance_id: str) -> Optional[InstanceData]:
        """Get instance data."""
        instance_key = RedisKeyPatterns.format_instance_info_key(instance_id)
        instance_data = await self.redis_client.get(instance_key)

        if not instance_data:
            return None

        try:
            data = json.loads(instance_data)
            return InstanceData.from_dict(instance_id, data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Failed to parse instance data for {instance_id}: {e}")
            return None

    async def get_pool_instances(self, graph_type: GraphType) -> List[str]:
        """Get all instance IDs for a graph type."""
        pool_key = RedisKeyPatterns.format_pool_instances_key(graph_type)
        instances = await self.redis_client.smembers(pool_key)
        return [
            instance.decode() if isinstance(instance, bytes) else instance
            for instance in instances
        ]

    async def update_instance_health(
        self,
        instance_id: str,
        status: GraphHealthStatus,
        load: float,
        last_heartbeat: Optional[datetime] = None,
    ) -> bool:
        """Update instance health status."""
        instance = await self.get_instance(instance_id)
        if not instance:
            return False

        instance.status = status
        instance.load = load
        instance.last_heartbeat = last_heartbeat or datetime.utcnow()

        instance_key = RedisKeyPatterns.format_instance_info_key(instance_id)
        await self.redis_client.setex(
            instance_key, 300, json.dumps(instance.to_dict())  # 5 minutes TTL
        )

        return True

    async def unregister_instance(self, instance_id: str) -> bool:
        """Unregister a graph instance."""
        instance = await self.get_instance(instance_id)
        if not instance:
            return False

        # Remove from pool instances set
        pool_key = RedisKeyPatterns.format_pool_instances_key(instance.graph_type)
        await self.redis_client.srem(pool_key, instance_id)

        # Delete instance data
        instance_key = RedisKeyPatterns.format_instance_info_key(instance_id)
        deleted = await self.redis_client.delete(instance_key)

        if deleted:
            self.logger.info(f"Unregistered instance {instance_id}")

        return bool(deleted)

    # Usage Tracking
    async def track_usage(
        self,
        user_id: Union[str, UUID],
        date: str,
        requests: int = 1,
        tokens: int = 0,
        processing_time: float = 0.0,
    ) -> Dict[str, int]:
        """Track user usage for a specific date."""
        usage_key = RedisKeyPatterns.format_usage_tracking_key(user_id, date)

        # Get current usage
        current_usage = await self.redis_client.hgetall(usage_key)
        current_requests = int(current_usage.get(b"requests", 0))
        current_tokens = int(current_usage.get(b"tokens", 0))
        current_processing_time = float(current_usage.get(b"processing_time", 0.0))

        # Update usage
        new_requests = current_requests + requests
        new_tokens = current_tokens + tokens
        new_processing_time = current_processing_time + processing_time

        await self.redis_client.hset(
            usage_key,
            mapping={
                "requests": new_requests,
                "tokens": new_tokens,
                "processing_time": new_processing_time,
                "last_updated": datetime.utcnow().isoformat(),
            },
        )

        # Set TTL to end of month
        await self.redis_client.expireat(
            usage_key, int((datetime.utcnow() + timedelta(days=31)).timestamp())
        )

        return {
            "requests": new_requests,
            "tokens": new_tokens,
            "processing_time": new_processing_time,
        }

    async def get_usage(self, user_id: Union[str, UUID], date: str) -> Dict[str, int]:
        """Get user usage for a specific date."""
        usage_key = RedisKeyPatterns.format_usage_tracking_key(user_id, date)
        usage = await self.redis_client.hgetall(usage_key)

        return {
            "requests": int(usage.get(b"requests", 0)),
            "tokens": int(usage.get(b"tokens", 0)),
            "processing_time": float(usage.get(b"processing_time", 0.0)),
        }

    # Rate Limiting
    async def check_rate_limit(
        self, user_id: Union[str, UUID], endpoint: str, limit: int, window: int = 60
    ) -> Dict[str, Any]:
        """Check if user has exceeded rate limit for endpoint."""
        rate_limit_key = RedisKeyPatterns.format_rate_limit_key(user_id, endpoint)

        # Get current count
        current_count = await self.redis_client.get(rate_limit_key)
        current_count = int(current_count) if current_count else 0

        if current_count >= limit:
            # Rate limit exceeded
            ttl = await self.redis_client.ttl(rate_limit_key)
            return {
                "allowed": False,
                "current_count": current_count,
                "limit": limit,
                "reset_after": ttl if ttl > 0 else window,
            }

        # Increment counter
        if current_count == 0:
            # First request in window
            await self.redis_client.setex(rate_limit_key, window, 1)
        else:
            await self.redis_client.incr(rate_limit_key)

        return {
            "allowed": True,
            "current_count": current_count + 1,
            "limit": limit,
            "reset_after": window,
        }

    # Caching
    async def cache_set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set cache value."""
        try:
            serialized_value = (
                json.dumps(value) if not isinstance(value, str) else value
            )
            await self.redis_client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            self.logger.error(f"Failed to set cache value for key {key}: {e}")
            return False

    async def cache_get(self, key: str) -> Optional[Any]:
        """Get cache value."""
        try:
            value = await self.redis_client.get(key)
            if value is None:
                return None

            # Try to deserialize as JSON, fallback to string
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value.decode() if isinstance(value, bytes) else value
        except Exception as e:
            self.logger.error(f"Failed to get cache value for key {key}: {e}")
            return None

    async def cache_delete(self, key: str) -> bool:
        """Delete cache value."""
        try:
            deleted = await self.redis_client.delete(key)
            return bool(deleted)
        except Exception as e:
            self.logger.error(f"Failed to delete cache value for key {key}: {e}")
            return False

    # Locking
    async def acquire_lock(
        self, lock_key: str, timeout: int = 10, blocking_timeout: int = 5
    ) -> bool:
        """Acquire a distributed lock."""
        try:
            # Try to acquire lock with timeout
            acquired = await self.redis_client.set(
                lock_key, "locked", nx=True, ex=timeout  # Only set if not exists
            )
            return bool(acquired)
        except Exception as e:
            self.logger.error(f"Failed to acquire lock {lock_key}: {e}")
            return False

    async def release_lock(self, lock_key: str) -> bool:
        """Release a distributed lock."""
        try:
            deleted = await self.redis_client.delete(lock_key)
            return bool(deleted)
        except Exception as e:
            self.logger.error(f"Failed to release lock {lock_key}: {e}")
            return False


# Global Redis manager instance
_redis_manager: Optional[RedisManager] = None


def get_redis_manager(redis_client: Optional[redis.Redis] = None) -> RedisManager:
    """Get the global Redis manager instance."""
    global _redis_manager

    if _redis_manager is None:
        if redis_client is None:
            raise ConfigurationError(
                "Redis client is required to initialize Redis manager"
            )
        _redis_manager = RedisManager(redis_client)

    return _redis_manager


def create_redis_manager(redis_client: redis.Redis) -> RedisManager:
    """Create a new Redis manager instance."""
    return RedisManager(redis_client)
