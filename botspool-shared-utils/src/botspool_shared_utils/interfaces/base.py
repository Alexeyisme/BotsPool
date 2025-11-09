"""
Base interfaces and protocols for services and repositories
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from datetime import datetime

T = TypeVar("T")
K = TypeVar("K")


class ServiceInterface(ABC):
    """
    Abstract base class for all services.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the service."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the service."""
        pass

    @property
    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if the service is healthy."""
        pass


class RepositoryInterface(ABC, Generic[T, K]):
    """
    Abstract base class for all repositories.
    """

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: K) -> Optional[T]:
        """Get an entity by its ID."""
        pass

    @abstractmethod
    async def get_all(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[T]:
        """Get all entities with optional pagination."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, entity_id: K) -> bool:
        """Delete an entity by its ID."""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Count the total number of entities."""
        pass

    @abstractmethod
    async def exists(self, entity_id: K) -> bool:
        """Check if an entity exists."""
        pass


class CacheInterface(ABC):
    """
    Abstract base class for cache implementations.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all values from the cache."""
        pass

    @abstractmethod
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get the TTL for a key."""
        pass

    @abstractmethod
    async def set_ttl(self, key: str, ttl: int) -> bool:
        """Set the TTL for a key."""
        pass


class MessageQueueInterface(ABC):
    """
    Abstract base class for message queue implementations.
    """

    @abstractmethod
    async def publish(self, topic: str, message: Any) -> bool:
        """Publish a message to a topic."""
        pass

    @abstractmethod
    async def subscribe(self, topic: str, callback: callable) -> str:
        """Subscribe to a topic."""
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a topic."""
        pass

    @abstractmethod
    async def consume(self, topic: str, timeout: Optional[int] = None) -> Optional[Any]:
        """Consume a message from a topic."""
        pass


class EventBusInterface(ABC):
    """
    Abstract base class for event bus implementations.
    """

    @abstractmethod
    async def emit(self, event_type: str, data: Any) -> None:
        """Emit an event."""
        pass

    @abstractmethod
    async def on(self, event_type: str, handler: callable) -> str:
        """Register an event handler."""
        pass

    @abstractmethod
    async def off(self, handler_id: str) -> bool:
        """Unregister an event handler."""
        pass

    @abstractmethod
    async def once(self, event_type: str, handler: callable) -> str:
        """Register a one-time event handler."""
        pass


class MetricsInterface(ABC):
    """
    Abstract base class for metrics implementations.
    """

    @abstractmethod
    async def increment(
        self,
        metric_name: str,
        value: float = 1.0,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Increment a counter metric."""
        pass

    @abstractmethod
    async def gauge(
        self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge metric."""
        pass

    @abstractmethod
    async def histogram(
        self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a histogram metric."""
        pass

    @abstractmethod
    async def timer(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        """Create a timer context manager."""
        pass


class ConfigurationInterface(ABC):
    """
    Abstract base class for configuration implementations.
    """

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        pass

    @abstractmethod
    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a configuration key."""
        pass

    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        pass

    @abstractmethod
    def reload(self) -> None:
        """Reload configuration from source."""
        pass
