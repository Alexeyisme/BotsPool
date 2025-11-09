"""Reusable gateway registration service."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

import httpx

from botspool_shared_utils.models.enums import GraphType

logger = logging.getLogger(__name__)


@dataclass
class RegistrationConfig:
    """Configuration payload for gateway registration."""

    gateway_url: str
    register_endpoint: str
    instance_id: str
    graph_type: Union[GraphType, str]
    endpoint: str
    capacity: int
    version: str
    interval_seconds: int = 30
    request_timeout: float = 10.0
    extra_headers: Dict[str, str] = field(default_factory=dict)
    extra_payload: Dict[str, Any] = field(default_factory=dict)

    def payload(self) -> Dict[str, Any]:
        """Serialise the registration payload expected by the gateway."""

        graph_type_value = (
            self.graph_type.value
            if isinstance(self.graph_type, GraphType)
            else self.graph_type
        )

        base_payload: Dict[str, Any] = {
            "instance_id": self.instance_id,
            "graph_type": graph_type_value,
            "endpoint": self.endpoint,
            "capacity": self.capacity,
            "version": self.version,
        }

        base_payload.update(self.extra_payload)
        return base_payload


class GatewayRegistrationService:
    """Generic service for registering graph instances with the gateway."""

    def __init__(self, config: RegistrationConfig):
        self._config = config
        self._is_running = False
        self._task: Optional[asyncio.Task[None]] = None
        self._logger = logging.getLogger(self.__class__.__name__)

        if not self._config.gateway_url.endswith(
            "/"
        ) and not self._config.register_endpoint.startswith("/"):
            # Avoid subtle mistakes with URL concatenation
            self._endpoint = (
                f"{self._config.gateway_url}/{self._config.register_endpoint}"
            )
        else:
            self._endpoint = (
                f"{self._config.gateway_url}{self._config.register_endpoint}"
            )

    async def start(self) -> None:
        """Start the registration heartbeat."""

        if self._is_running:
            return

        self._is_running = True
        self._task = asyncio.create_task(self._run_loop())
        self._logger.info(
            "Gateway registration service started for instance '%s'",
            self._config.instance_id,
        )

    async def stop(self) -> None:
        """Stop the registration heartbeat."""

        if not self._is_running:
            return

        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._logger.info(
            "Gateway registration service stopped for instance '%s'",
            self._config.instance_id,
        )

    async def update_load(self, load: int) -> None:
        """Optionally inform the gateway of load changes (currently reuses registration payload)."""

        await self._register(extra_payload={"current_load": load})

    async def update_status(self, status: str) -> None:
        """Optionally inform the gateway of status updates (currently reuses registration payload)."""

        await self._register(extra_payload={"status": status})

    async def _run_loop(self) -> None:
        """Background loop that periodically registers with the gateway."""

        try:
            while self._is_running:
                await self._register()
                await asyncio.sleep(self._config.interval_seconds)
        except asyncio.CancelledError:
            self._logger.debug("Gateway registration loop cancelled")
        except Exception as exc:
            self._logger.exception("Gateway registration loop error: %s", exc)
            await asyncio.sleep(self._config.interval_seconds)
            if self._is_running:
                self._task = asyncio.create_task(self._run_loop())

    async def _register(self, extra_payload: Optional[Dict[str, Any]] = None) -> None:
        """Send a registration request to the gateway."""

        payload = self._config.payload()
        if extra_payload:
            payload = {**payload, **extra_payload}

        headers = {"Content-Type": "application/json", **self._config.extra_headers}

        try:
            async with httpx.AsyncClient(
                timeout=self._config.request_timeout
            ) as client:
                response = await client.post(
                    self._endpoint, json=payload, headers=headers
                )

            if response.status_code in (200, 201):
                self._logger.debug(
                    "Successfully registered instance '%s' with gateway",
                    self._config.instance_id,
                )
            else:
                self._logger.warning(
                    "Gateway registration failed (%s): %s",
                    response.status_code,
                    response.text,
                )

        except httpx.TimeoutException:
            self._logger.warning(
                "Gateway registration timeout for '%s'", self._config.instance_id
            )
        except httpx.ConnectError:
            self._logger.warning(
                "Cannot connect to gateway for instance '%s'", self._config.instance_id
            )
        except Exception as exc:  # pragma: no cover - unexpected network failure
            self._logger.error(
                "Gateway registration error for '%s': %s", self._config.instance_id, exc
            )

    def get_instance_info(self) -> Dict[str, Any]:
        """Return the static registration payload (without extras)."""

        payload = self._config.payload().copy()
        payload.pop("instance_id", None)
        return payload
