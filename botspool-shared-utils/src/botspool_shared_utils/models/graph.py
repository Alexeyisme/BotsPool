"""
Graph-related models for BotsPool

This module contains all models related to AI graph management,
including graph instances, health monitoring, and configuration.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .base import BaseEntity, TimestampMixin
from .enums import GraphType, GraphStatus


class GraphConfig(BaseModel):
    """
    Graph configuration model.

    Stores configuration parameters for AI graphs.
    """

    # Model configuration
    model_name: str = Field(..., description="AI model name")
    model_version: str = Field(..., description="AI model version")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: int = Field(1000, ge=1, description="Maximum tokens per response")

    # Graph-specific configuration
    tools_enabled: List[str] = Field(default_factory=list, description="Enabled tools")
    memory_enabled: bool = Field(True, description="Memory enabled")
    memory_size: int = Field(100, ge=1, description="Memory size")

    # Performance configuration
    timeout_seconds: int = Field(30, ge=1, description="Request timeout")
    max_concurrent_requests: int = Field(
        10, ge=1, description="Max concurrent requests"
    )

    # Feature flags
    features: Dict[str, bool] = Field(default_factory=dict, description="Feature flags")

    # Custom parameters
    custom_params: Dict[str, Any] = Field(
        default_factory=dict, description="Custom parameters"
    )


class GraphHealth(BaseModel):
    """
    Graph health status model.

    Tracks the health and performance of graph instances.
    """

    instance_id: str = Field(..., description="Graph instance ID")
    status: GraphStatus = Field(..., description="Health status")

    # Performance metrics
    response_time_avg: float = Field(0.0, ge=0, description="Average response time")
    response_time_p95: float = Field(
        0.0, ge=0, description="95th percentile response time"
    )
    requests_per_minute: float = Field(0.0, ge=0, description="Requests per minute")
    error_rate: float = Field(0.0, ge=0, le=1, description="Error rate")

    # Resource usage
    cpu_usage: float = Field(0.0, ge=0, le=100, description="CPU usage percentage")
    memory_usage: float = Field(
        0.0, ge=0, le=100, description="Memory usage percentage"
    )

    # Request statistics
    total_requests: int = Field(0, ge=0, description="Total requests")
    successful_requests: int = Field(0, ge=0, description="Successful requests")
    failed_requests: int = Field(0, ge=0, description="Failed requests")

    # Timestamps
    last_health_check: datetime = Field(
        default_factory=datetime.utcnow, description="Last health check"
    )
    last_request_at: Optional[datetime] = Field(
        None, description="Last request timestamp"
    )

    def update_metrics(self, response_time: float, success: bool) -> None:
        """Update health metrics with new request data."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        # Update response time (simple moving average)
        if self.response_time_avg == 0:
            self.response_time_avg = response_time
        else:
            self.response_time_avg = (self.response_time_avg * 0.9) + (
                response_time * 0.1
            )

        # Update error rate
        self.error_rate = (
            self.failed_requests / self.total_requests if self.total_requests > 0 else 0
        )

        self.last_request_at = datetime.utcnow()

    def is_healthy(self) -> bool:
        """Check if the graph instance is healthy."""
        return (
            self.status == GraphStatus.HEALTHY
            and self.error_rate < 0.1
            and self.response_time_avg  # Less than 10% error rate
            < 5.0  # Less than 5 seconds average response time
        )


class GraphInstance(BaseEntity):
    """
    Graph instance model.

    Represents a running instance of an AI graph.
    """

    graph_type: GraphType = Field(..., description="Graph type")
    instance_id: str = Field(..., description="Unique instance identifier")

    # Instance information
    version: str = Field(..., description="Graph version")
    endpoint: str = Field(..., description="Instance endpoint URL")
    region: str = Field("us-east-1", description="Deployment region")

    # Status and health
    status: GraphStatus = Field(GraphStatus.OFFLINE, description="Instance status")
    health: GraphHealth = Field(..., description="Health information")

    # Configuration
    config: GraphConfig = Field(..., description="Graph configuration")

    # Capacity and load
    max_capacity: int = Field(100, ge=1, description="Maximum concurrent requests")
    current_load: int = Field(0, ge=0, description="Current request load")

    # Deployment information
    deployment_id: Optional[str] = Field(None, description="Deployment ID")
    container_id: Optional[str] = Field(None, description="Container ID")

    # Timestamps
    started_at: Optional[datetime] = Field(None, description="Instance start time")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat")

    def register(self) -> None:
        """Register the instance as online."""
        self.status = GraphStatus.HEALTHY
        self.started_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def heartbeat(self) -> None:
        """Update heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_unhealthy(self) -> None:
        """Mark instance as unhealthy."""
        self.status = GraphStatus.UNHEALTHY
        self.updated_at = datetime.utcnow()

    def mark_maintenance(self) -> None:
        """Mark instance for maintenance."""
        self.status = GraphStatus.MAINTENANCE
        self.updated_at = datetime.utcnow()

    def increment_load(self) -> None:
        """Increment current load."""
        self.current_load += 1
        self.updated_at = datetime.utcnow()

    def decrement_load(self) -> None:
        """Decrement current load."""
        self.current_load = max(0, self.current_load - 1)
        self.updated_at = datetime.utcnow()

    def is_available(self) -> bool:
        """Check if instance is available for requests."""
        return (
            self.status == GraphStatus.HEALTHY
            and self.current_load < self.max_capacity
            and self.health.is_healthy()
        )

    def get_load_percentage(self) -> float:
        """Get current load as percentage of capacity."""
        return (self.current_load / self.max_capacity) * 100


class Graph(BaseEntity):
    """
    Graph model.

    Represents an AI graph type with its metadata and instances.
    """

    graph_type: GraphType = Field(..., description="Graph type")
    name: str = Field(..., description="Graph name")
    description: str = Field(..., description="Graph description")

    # Graph metadata
    version: str = Field(..., description="Graph version")
    author: str = Field(..., description="Graph author")
    tags: List[str] = Field(default_factory=list, description="Graph tags")

    # Status and availability
    status: GraphStatus = Field(GraphStatus.OFFLINE, description="Graph status")
    is_available: bool = Field(False, description="Graph availability")

    # Configuration
    default_config: GraphConfig = Field(..., description="Default configuration")

    # Instances
    instances: List[GraphInstance] = Field(
        default_factory=list, description="Graph instances"
    )

    # Statistics
    total_requests: int = Field(0, ge=0, description="Total requests")
    total_users: int = Field(0, ge=0, description="Total users")

    # Timestamps
    last_deployment: Optional[datetime] = Field(None, description="Last deployment")

    def add_instance(self, instance: GraphInstance) -> None:
        """Add a new instance to the graph."""
        self.instances.append(instance)
        self.update_status()
        self.updated_at = datetime.utcnow()

    def remove_instance(self, instance_id: str) -> None:
        """Remove an instance from the graph."""
        self.instances = [i for i in self.instances if i.instance_id != instance_id]
        self.update_status()
        self.updated_at = datetime.utcnow()

    def update_status(self) -> None:
        """Update graph status based on instances."""
        if not self.instances:
            self.status = GraphStatus.OFFLINE
            self.is_available = False
            return

        healthy_instances = [i for i in self.instances if i.is_available()]

        if not healthy_instances:
            self.status = GraphStatus.UNHEALTHY
            self.is_available = False
        elif len(healthy_instances) < len(self.instances):
            self.status = GraphStatus.DEGRADED
            self.is_available = True
        else:
            self.status = GraphStatus.HEALTHY
            self.is_available = True

    def get_available_instances(self) -> List[GraphInstance]:
        """Get all available instances."""
        return [i for i in self.instances if i.is_available()]

    def get_best_instance(
        self, strategy: str = "least_loaded"
    ) -> Optional[GraphInstance]:
        """Get the best instance based on strategy."""
        available_instances = self.get_available_instances()

        if not available_instances:
            return None

        if strategy == "least_loaded":
            return min(available_instances, key=lambda i: i.current_load)
        elif strategy == "fastest":
            return min(available_instances, key=lambda i: i.health.response_time_avg)
        elif strategy == "round_robin":
            # Simple round-robin (could be improved with state)
            return available_instances[0]

        return available_instances[0]

    def get_total_capacity(self) -> int:
        """Get total capacity across all instances."""
        return sum(i.max_capacity for i in self.instances)

    def get_current_load(self) -> int:
        """Get current total load across all instances."""
        return sum(i.current_load for i in self.instances)

    def get_load_percentage(self) -> float:
        """Get current load as percentage of total capacity."""
        total_capacity = self.get_total_capacity()
        if total_capacity == 0:
            return 0.0
        return (self.get_current_load() / total_capacity) * 100


class GraphDeployment(BaseModel):
    """
    Graph deployment model.

    Represents a deployment of a graph instance.
    """

    deployment_id: str = Field(..., description="Deployment ID")
    graph_type: GraphType = Field(..., description="Graph type")
    version: str = Field(..., description="Graph version")

    # Deployment configuration
    config: GraphConfig = Field(..., description="Deployment configuration")
    replicas: int = Field(1, ge=1, description="Number of replicas")

    # Status
    status: str = Field("pending", description="Deployment status")
    progress: float = Field(0.0, ge=0, le=100, description="Deployment progress")

    # Timestamps
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="Deployment start time"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Deployment completion time"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Deployment metadata"
    )


class GraphMetrics(BaseModel):
    """
    Graph metrics model.

    Aggregated metrics for a graph type.
    """

    graph_type: GraphType = Field(..., description="Graph type")

    # Request metrics
    total_requests: int = Field(0, ge=0, description="Total requests")
    successful_requests: int = Field(0, ge=0, description="Successful requests")
    failed_requests: int = Field(0, ge=0, description="Failed requests")

    # Performance metrics
    average_response_time: float = Field(0.0, ge=0, description="Average response time")
    p95_response_time: float = Field(
        0.0, ge=0, description="95th percentile response time"
    )
    requests_per_minute: float = Field(0.0, ge=0, description="Requests per minute")

    # Error metrics
    error_rate: float = Field(0.0, ge=0, le=1, description="Error rate")
    error_types: Dict[str, int] = Field(
        default_factory=dict, description="Error types count"
    )

    # User metrics
    unique_users: int = Field(0, ge=0, description="Unique users")
    active_sessions: int = Field(0, ge=0, description="Active sessions")

    # Time window
    time_window_start: datetime = Field(..., description="Metrics window start")
    time_window_end: datetime = Field(..., description="Metrics window end")

    def calculate_error_rate(self) -> float:
        """Calculate error rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests
