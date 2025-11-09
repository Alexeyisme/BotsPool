"""Data models for notification service"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class NotificationPriority(str, Enum):
    """Notification priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationType(str, Enum):
    """Types of notifications"""

    REMINDER = "reminder"
    ALERT = "alert"
    INFO = "info"
    UPDATE = "update"


class NotificationStatus(str, Enum):
    """Notification delivery status"""

    PENDING = "pending"
    DISPATCHED = "dispatched"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FrontendType(str, Enum):
    """Supported frontend types"""

    TELEGRAM = "telegram"
    DISCORD = "discord"  # Future
    WEB = "web"  # Future


class NotificationRequest(BaseModel):
    """Notification request from agent"""

    user_id: str = Field(..., description="BotsPool user UUID")
    chat_id: int = Field(..., description="Frontend-specific chat ID")
    frontend: FrontendType = Field(FrontendType.TELEGRAM, description="Target frontend")
    message: str = Field(
        ..., min_length=1, max_length=4000, description="Notification message"
    )
    agent: str = Field(..., description="Which agent sent it")
    priority: NotificationPriority = Field(
        NotificationPriority.NORMAL, description="Priority level"
    )
    notification_type: NotificationType = Field(
        NotificationType.INFO, description="Notification type"
    )
    scheduled_for: Optional[datetime] = Field(
        None, description="For scheduled notifications"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )


class ScheduledNotification(BaseModel):
    """Scheduled notification stored in Redis"""

    id: str = Field(..., description="Unique notification ID (UUID)")
    user_id: str
    chat_id: int
    frontend: FrontendType
    message: str
    agent: str
    priority: NotificationPriority
    notification_type: NotificationType
    status: NotificationStatus = NotificationStatus.PENDING
    created_at: datetime
    scheduled_for: datetime
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeliveryStatus(BaseModel):
    """Delivery status tracking"""

    notification_id: str
    status: NotificationStatus
    delivered_at: Optional[datetime] = None
    attempts: int = 0
    last_error: Optional[str] = None


class NotificationResponse(BaseModel):
    """Response for created notification"""

    notification_id: str
    status: NotificationStatus
    scheduled_for: Optional[datetime] = None
    timestamp: datetime


class NotificationListResponse(BaseModel):
    """Response for listing notifications"""

    notifications: list[ScheduledNotification]
    total: int


class BotNotificationRequest(BaseModel):
    """Notification request sent to bot"""

    chat_id: int
    message: str
    agent: str
    notification_type: NotificationType
    priority: NotificationPriority


class BotNotificationResponse(BaseModel):
    """Response from bot"""

    status: str
    delivered_at: datetime
