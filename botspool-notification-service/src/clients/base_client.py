"""Base frontend client interface"""
from abc import ABC, abstractmethod
from typing import Dict, Any

from ..models import BotNotificationRequest, BotNotificationResponse


class BaseFrontendClient(ABC):
    """Abstract base class for frontend clients"""

    @abstractmethod
    async def send_notification(
        self, request: BotNotificationRequest
    ) -> BotNotificationResponse:
        """
        Send notification to frontend.

        Args:
            request: Notification request

        Returns:
            Delivery response
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if frontend is healthy.

        Returns:
            True if healthy
        """
        pass
