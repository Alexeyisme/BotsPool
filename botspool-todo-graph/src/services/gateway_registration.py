"""Factory for the ToDo graph gateway registration service."""

from botspool_shared_utils.gateway import (
    GatewayRegistrationService as BaseGatewayRegistrationService,
    RegistrationConfig,
)
from botspool_shared_utils.models.enums import GraphType

from ..config import Settings


class GatewayRegistrationService(BaseGatewayRegistrationService):
    """ToDo graph-specific configuration for the shared gateway registration service."""

    def __init__(self, settings: Settings):
        config = RegistrationConfig(
            gateway_url=settings.gateway_url,
            register_endpoint=settings.gateway_register_endpoint,
            instance_id=settings.instance_id,
            graph_type=GraphType.TODO,
            endpoint=settings.graph_endpoint,
            capacity=settings.graph_capacity,
            version=settings.graph_version,
            interval_seconds=settings.health_check_interval,
        )
        super().__init__(config)
