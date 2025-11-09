"""
Graph management API endpoints for BotsPool Gateway

This module provides endpoints for:
- Graph instance registration
- Service discovery
- Health monitoring
- Graph status reporting
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from botspool_shared_utils.models.enums import GraphType
from botspool_shared_utils.errors import ValidationError, ErrorCode

from ...auth.middleware import get_current_user_required, require_admin
from ...graphs.registry import GraphRegistry, GraphInstance, get_graph_registry
from ...dependencies import get_redis_client

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/graphs", tags=["Graphs"])


# Request/Response Models
class GraphRegistrationRequest(BaseModel):
    """Graph instance registration request."""

    instance_id: str = Field(
        ..., min_length=1, max_length=100, description="Unique instance identifier"
    )
    graph_type: GraphType = Field(..., description="Type of graph")
    endpoint: str = Field(..., description="Instance endpoint URL")
    capacity: int = Field(
        default=100, ge=1, le=1000, description="Maximum concurrent requests"
    )
    version: str = Field(default="1.0.0", description="Instance version")


class GraphRegistrationResponse(BaseModel):
    """Graph instance registration response."""

    success: bool = Field(..., description="Registration success status")
    message: str = Field(..., description="Registration message")
    instance_id: str = Field(..., description="Registered instance ID")


class GraphStatusResponse(BaseModel):
    """Graph status response."""

    graph_type: str = Field(..., description="Graph type")
    total_instances: int = Field(..., description="Total instances")
    healthy_instances: int = Field(..., description="Healthy instances")
    unhealthy_instances: int = Field(..., description="Unhealthy instances")
    instances: List[Dict[str, Any]] = Field(..., description="Instance details")


class GraphListResponse(BaseModel):
    """Graph list response."""

    graphs: List[Dict[str, Any]] = Field(..., description="Available graphs")
    total_graphs: int = Field(..., description="Total number of graphs")


class RegistryStatsResponse(BaseModel):
    """Registry statistics response."""

    total_instances: int = Field(..., description="Total instances")
    healthy_instances: int = Field(..., description="Healthy instances")
    unhealthy_instances: int = Field(..., description="Unhealthy instances")
    by_graph_type: Dict[str, int] = Field(..., description="Instances by graph type")
    by_status: Dict[str, int] = Field(..., description="Instances by status")


@router.post("/register", response_model=GraphRegistrationResponse)
async def register_graph_instance(
    request: GraphRegistrationRequest,
    registry: GraphRegistry = Depends(get_graph_registry),
):
    """
    Register a new graph instance.

    Allows graph instances to register themselves with the gateway
    for service discovery and load balancing.

    Args:
        request: Registration request data
        registry: Graph registry instance

    Returns:
        GraphRegistrationResponse: Registration result

    Raises:
        HTTPException: If registration fails
    """
    try:
        # Register instance
        success = await registry.register_instance(
            instance_id=request.instance_id,
            graph_type=request.graph_type,
            endpoint=request.endpoint,
            capacity=request.capacity,
            version=request.version,
        )

        if success:
            logger.info(
                f"Graph instance registered: {request.instance_id} ({request.graph_type.value})"
            )
            return GraphRegistrationResponse(
                success=True,
                message="Instance registered successfully",
                instance_id=request.instance_id,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register instance",
            )

    except Exception as exc:
        logger.error(f"Graph registration failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(exc)}",
        )


@router.delete("/unregister/{instance_id}")
async def unregister_graph_instance(
    instance_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    registry: GraphRegistry = Depends(get_graph_registry),
):
    """
    Unregister a graph instance.

    Removes a graph instance from the registry.

    Args:
        instance_id: Instance identifier
        current_user: Current authenticated user
        registry: Graph registry instance

    Returns:
        dict: Unregistration result
    """
    try:
        success = await registry.unregister_instance(instance_id)

        if success:
            logger.info(f"Graph instance unregistered: {instance_id}")
            return {"success": True, "message": "Instance unregistered successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found"
            )

    except Exception as exc:
        logger.error(f"Graph unregistration failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unregistration failed: {str(exc)}",
        )


@router.get("/", response_model=GraphListResponse)
async def list_available_graphs(
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    registry: GraphRegistry = Depends(get_graph_registry),
):
    """
    List all available graph types.

    Returns information about all registered graph types and their instances.

    Args:
        current_user: Current authenticated user
        registry: Graph registry instance

    Returns:
        GraphListResponse: List of available graphs
    """
    try:
        all_instances = await registry.get_all_instances()

        # Group instances by graph type
        graphs_by_type = {}
        for instance in all_instances:
            graph_type = instance.graph_type.value
            if graph_type not in graphs_by_type:
                graphs_by_type[graph_type] = {
                    "type": graph_type,
                    "total_instances": 0,
                    "healthy_instances": 0,
                    "instances": [],
                }

            graphs_by_type[graph_type]["total_instances"] += 1
            if registry._is_instance_healthy(instance):
                graphs_by_type[graph_type]["healthy_instances"] += 1

            graphs_by_type[graph_type]["instances"].append(
                {
                    "instance_id": instance.instance_id,
                    "endpoint": instance.endpoint,
                    "status": instance.status,
                    "capacity": instance.capacity,
                    "current_load": instance.current_load,
                    "version": instance.version,
                    "last_heartbeat": instance.last_heartbeat.isoformat(),
                }
            )

        graphs = list(graphs_by_type.values())

        return GraphListResponse(graphs=graphs, total_graphs=len(graphs))

    except Exception as exc:
        logger.error(f"Failed to list graphs: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list graphs: {str(exc)}",
        )


@router.get("/{graph_type}/status", response_model=GraphStatusResponse)
async def get_graph_status(
    graph_type: GraphType,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    registry: GraphRegistry = Depends(get_graph_registry),
):
    """
    Get status of a specific graph type.

    Returns detailed status information for all instances of a graph type.

    Args:
        graph_type: Graph type to check
        current_user: Current authenticated user
        registry: Graph registry instance

    Returns:
        GraphStatusResponse: Graph status information
    """
    try:
        # Get all instances of this graph type
        all_instances = await registry.get_instances_by_type(graph_type)
        healthy_instances = await registry.get_healthy_instances(graph_type)

        # Prepare instance details
        instance_details = []
        for instance in all_instances:
            instance_details.append(
                {
                    "instance_id": instance.instance_id,
                    "endpoint": instance.endpoint,
                    "status": instance.status,
                    "capacity": instance.capacity,
                    "current_load": instance.current_load,
                    "version": instance.version,
                    "last_heartbeat": instance.last_heartbeat.isoformat(),
                    "healthy": registry._is_instance_healthy(instance),
                }
            )

        return GraphStatusResponse(
            graph_type=graph_type.value,
            total_instances=len(all_instances),
            healthy_instances=len(healthy_instances),
            unhealthy_instances=len(all_instances) - len(healthy_instances),
            instances=instance_details,
        )

    except Exception as exc:
        logger.error(f"Failed to get graph status for {graph_type.value}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get graph status: {str(exc)}",
        )


@router.get("/stats", response_model=RegistryStatsResponse)
async def get_registry_stats(
    current_user: Dict[str, Any] = Depends(require_admin),
    registry: GraphRegistry = Depends(get_graph_registry),
):
    """
    Get registry statistics.

    Returns comprehensive statistics about the graph registry.
    Requires admin access.

    Args:
        current_user: Current authenticated user (admin required)
        registry: Graph registry instance

    Returns:
        RegistryStatsResponse: Registry statistics
    """
    try:
        stats = await registry.get_registry_stats()

        return RegistryStatsResponse(
            total_instances=stats.get("total_instances", 0),
            healthy_instances=stats.get("healthy_instances", 0),
            unhealthy_instances=stats.get("unhealthy_instances", 0),
            by_graph_type=stats.get("by_graph_type", {}),
            by_status=stats.get("by_status", {}),
        )

    except Exception as exc:
        logger.error(f"Failed to get registry stats: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get registry stats: {str(exc)}",
        )


@router.post("/cleanup")
async def cleanup_stale_instances(
    current_user: Dict[str, Any] = Depends(require_admin),
    registry: GraphRegistry = Depends(get_graph_registry),
):
    """
    Clean up stale instances.

    Removes instances that haven't sent heartbeats recently.
    Requires admin access.

    Args:
        current_user: Current authenticated user (admin required)
        registry: Graph registry instance

    Returns:
        dict: Cleanup result
    """
    try:
        cleaned_count = await registry.cleanup_stale_instances()

        logger.info(f"Cleaned up {cleaned_count} stale instances")
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} stale instances",
            "cleaned_count": cleaned_count,
        }

    except Exception as exc:
        logger.error(f"Failed to cleanup stale instances: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(exc)}",
        )


@router.post("/heartbeat/{instance_id}")
async def update_heartbeat(
    instance_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    registry: GraphRegistry = Depends(get_graph_registry),
):
    """
    Update instance heartbeat.

    Allows graph instances to update their heartbeat timestamp.

    Args:
        instance_id: Instance identifier
        current_user: Current authenticated user
        registry: Graph registry instance

    Returns:
        dict: Heartbeat update result
    """
    try:
        success = await registry.update_heartbeat(instance_id)

        if success:
            return {"success": True, "message": "Heartbeat updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found"
            )

    except Exception as exc:
        logger.error(f"Failed to update heartbeat for {instance_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Heartbeat update failed: {str(exc)}",
        )
