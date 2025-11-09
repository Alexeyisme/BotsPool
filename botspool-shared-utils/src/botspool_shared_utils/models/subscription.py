"""
Subscription-related models for BotsPool

This module contains all models related to subscription management,
including plans, usage tracking, and billing.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .base import BaseEntity, TimestampMixin
from .enums import SubscriptionTier, GraphType


class UsageLimit(BaseModel):
    """
    Usage limit configuration.

    Defines limits for different subscription tiers.
    """

    # Request limits
    requests_per_minute: int = Field(..., ge=1, description="Requests per minute limit")
    requests_per_hour: int = Field(..., ge=1, description="Requests per hour limit")
    requests_per_day: int = Field(..., ge=1, description="Requests per day limit")
    requests_per_month: int = Field(..., ge=1, description="Requests per month limit")

    # Token limits
    tokens_per_request: int = Field(..., ge=1, description="Maximum tokens per request")
    tokens_per_day: int = Field(..., ge=1, description="Maximum tokens per day")
    tokens_per_month: int = Field(..., ge=1, description="Maximum tokens per month")

    # Graph access
    allowed_graphs: List[GraphType] = Field(..., description="Allowed graph types")
    max_concurrent_sessions: int = Field(
        ..., ge=1, description="Maximum concurrent sessions"
    )

    # Storage limits
    chat_history_retention_days: int = Field(
        ..., ge=1, description="Chat history retention in days"
    )
    max_file_upload_size_mb: int = Field(
        ..., ge=1, description="Maximum file upload size in MB"
    )

    # Feature flags
    features: Dict[str, bool] = Field(default_factory=dict, description="Feature flags")

    @validator("allowed_graphs")
    def validate_allowed_graphs(cls, v):
        """Validate that at least one graph is allowed."""
        if not v:
            raise ValueError("At least one graph type must be allowed")
        return v


class SubscriptionPlan(BaseModel):
    """
    Subscription plan definition.

    Defines a subscription plan with its features and limits.
    """

    tier: SubscriptionTier = Field(..., description="Subscription tier")
    name: str = Field(..., description="Plan name")
    description: str = Field(..., description="Plan description")

    # Pricing
    price_monthly: float = Field(..., ge=0, description="Monthly price in USD")
    price_yearly: float = Field(..., ge=0, description="Yearly price in USD")
    currency: str = Field("USD", description="Currency code")

    # Limits
    limits: UsageLimit = Field(..., description="Usage limits")

    # Features
    features: List[str] = Field(default_factory=list, description="Plan features")

    # Billing
    billing_cycle: str = Field("monthly", description="Billing cycle")
    trial_days: int = Field(0, ge=0, description="Trial period in days")

    # Status
    is_active: bool = Field(True, description="Plan active status")
    is_popular: bool = Field(False, description="Popular plan flag")

    def get_yearly_discount(self) -> float:
        """Calculate yearly discount percentage."""
        if self.price_yearly == 0:
            return 0.0

        monthly_yearly = self.price_monthly * 12
        if monthly_yearly == 0:
            return 0.0

        return ((monthly_yearly - self.price_yearly) / monthly_yearly) * 100


class UsageTracking(BaseModel):
    """
    Usage tracking for a user.

    Tracks current usage against limits.
    """

    user_id: UUID = Field(..., description="User ID")
    subscription_tier: SubscriptionTier = Field(..., description="Subscription tier")

    # Current usage (rolling windows)
    requests_current_minute: int = Field(0, ge=0, description="Current minute requests")
    requests_current_hour: int = Field(0, ge=0, description="Current hour requests")
    requests_current_day: int = Field(0, ge=0, description="Current day requests")
    requests_current_month: int = Field(0, ge=0, description="Current month requests")

    # Token usage
    tokens_current_day: int = Field(0, ge=0, description="Current day tokens")
    tokens_current_month: int = Field(0, ge=0, description="Current month tokens")

    # Session tracking
    active_sessions: int = Field(0, ge=0, description="Active sessions count")

    # Usage by graph
    usage_by_graph: Dict[str, int] = Field(
        default_factory=dict, description="Usage by graph type"
    )

    # Timestamps
    last_request_at: Optional[datetime] = Field(
        None, description="Last request timestamp"
    )
    last_reset_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last reset timestamp"
    )

    def increment_usage(self, graph_type: str, tokens_used: int = 0) -> None:
        """Increment usage counters."""
        self.requests_current_minute += 1
        self.requests_current_hour += 1
        self.requests_current_day += 1
        self.requests_current_month += 1

        self.tokens_current_day += tokens_used
        self.tokens_current_month += tokens_used

        self.usage_by_graph[graph_type] = self.usage_by_graph.get(graph_type, 0) + 1
        self.last_request_at = datetime.utcnow()

    def reset_minute_usage(self) -> None:
        """Reset minute usage counter."""
        self.requests_current_minute = 0

    def reset_hour_usage(self) -> None:
        """Reset hour usage counter."""
        self.requests_current_hour = 0

    def reset_daily_usage(self) -> None:
        """Reset daily usage counters."""
        self.requests_current_day = 0
        self.tokens_current_day = 0
        self.usage_by_graph.clear()
        self.last_reset_at = datetime.utcnow()

    def reset_monthly_usage(self) -> None:
        """Reset monthly usage counters."""
        self.requests_current_month = 0
        self.tokens_current_month = 0


class Subscription(BaseEntity):
    """
    User subscription model.

    Represents a user's subscription to the service.
    """

    user_id: UUID = Field(..., description="User ID")
    plan: SubscriptionPlan = Field(..., description="Subscription plan")

    # Subscription status
    status: str = Field("active", description="Subscription status")
    is_active: bool = Field(True, description="Subscription active status")

    # Billing information
    billing_cycle: str = Field("monthly", description="Billing cycle")
    next_billing_date: datetime = Field(..., description="Next billing date")
    last_billing_date: Optional[datetime] = Field(None, description="Last billing date")

    # Trial information
    is_trial: bool = Field(False, description="Trial subscription flag")
    trial_ends_at: Optional[datetime] = Field(None, description="Trial end date")

    # Payment information
    payment_method_id: Optional[str] = Field(None, description="Payment method ID")
    stripe_subscription_id: Optional[str] = Field(
        None, description="Stripe subscription ID"
    )

    # Usage tracking
    usage: UsageTracking = Field(..., description="Usage tracking")

    # Cancellation
    cancelled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    cancellation_reason: Optional[str] = Field(None, description="Cancellation reason")

    def is_trial_active(self) -> bool:
        """Check if trial is still active."""
        if not self.is_trial or not self.trial_ends_at:
            return False
        return datetime.utcnow() < self.trial_ends_at

    def days_until_billing(self) -> int:
        """Calculate days until next billing."""
        delta = self.next_billing_date - datetime.utcnow()
        return max(0, delta.days)

    def can_access_graph(self, graph_type: GraphType) -> bool:
        """Check if user can access a specific graph."""
        return graph_type in self.plan.limits.allowed_graphs

    def is_within_limits(self) -> bool:
        """Check if user is within usage limits."""
        limits = self.plan.limits

        return (
            self.usage.requests_current_minute <= limits.requests_per_minute
            and self.usage.requests_current_hour <= limits.requests_per_hour
            and self.usage.requests_current_day <= limits.requests_per_day
            and self.usage.requests_current_month <= limits.requests_per_month
            and self.usage.tokens_current_day <= limits.tokens_per_day
            and self.usage.tokens_current_month <= limits.tokens_per_month
            and self.usage.active_sessions <= limits.max_concurrent_sessions
        )

    def get_usage_percentage(self, limit_type: str) -> float:
        """Get usage percentage for a specific limit type."""
        limits = self.plan.limits

        if limit_type == "requests_per_day":
            return (self.usage.requests_current_day / limits.requests_per_day) * 100
        elif limit_type == "tokens_per_day":
            return (self.usage.tokens_current_day / limits.tokens_per_day) * 100
        elif limit_type == "requests_per_month":
            return (self.usage.requests_current_month / limits.requests_per_month) * 100
        elif limit_type == "tokens_per_month":
            return (self.usage.tokens_current_month / limits.tokens_per_month) * 100

        return 0.0

    def cancel(self, reason: str = None) -> None:
        """Cancel the subscription."""
        self.status = "cancelled"
        self.is_active = False
        self.cancelled_at = datetime.utcnow()
        self.cancellation_reason = reason
        self.updated_at = datetime.utcnow()

    def renew(self) -> None:
        """Renew the subscription."""
        self.status = "active"
        self.is_active = True
        self.last_billing_date = datetime.utcnow()

        # Calculate next billing date
        if self.billing_cycle == "monthly":
            self.next_billing_date = datetime.utcnow() + timedelta(days=30)
        elif self.billing_cycle == "yearly":
            self.next_billing_date = datetime.utcnow() + timedelta(days=365)

        self.updated_at = datetime.utcnow()


class SubscriptionCreate(BaseModel):
    """
    Model for creating a new subscription.

    Used in subscription creation endpoints.
    """

    user_id: UUID = Field(..., description="User ID")
    tier: SubscriptionTier = Field(..., description="Subscription tier")
    billing_cycle: str = Field("monthly", description="Billing cycle")
    payment_method_id: Optional[str] = Field(None, description="Payment method ID")
    trial_days: int = Field(0, ge=0, description="Trial period in days")


class SubscriptionUpdate(BaseModel):
    """
    Model for updating a subscription.

    Used in subscription update endpoints.
    """

    tier: Optional[SubscriptionTier] = Field(None, description="New subscription tier")
    billing_cycle: Optional[str] = Field(None, description="New billing cycle")
    payment_method_id: Optional[str] = Field(None, description="New payment method ID")


class SubscriptionResponse(BaseModel):
    """
    Model for subscription API responses.

    Used in subscription API endpoints.
    """

    id: UUID = Field(..., description="Subscription ID")
    user_id: UUID = Field(..., description="User ID")
    tier: SubscriptionTier = Field(..., description="Subscription tier")
    status: str = Field(..., description="Subscription status")
    is_active: bool = Field(..., description="Active status")
    billing_cycle: str = Field(..., description="Billing cycle")
    next_billing_date: datetime = Field(..., description="Next billing date")
    is_trial: bool = Field(..., description="Trial status")
    trial_ends_at: Optional[datetime] = Field(None, description="Trial end date")
    created_at: datetime = Field(..., description="Creation timestamp")

    # Usage information
    usage: Dict[str, Any] = Field(..., description="Current usage")
    limits: Dict[str, Any] = Field(..., description="Usage limits")

    @classmethod
    def from_subscription(cls, subscription: Subscription) -> "SubscriptionResponse":
        """Create SubscriptionResponse from Subscription model."""
        return cls(
            id=subscription.id,
            user_id=subscription.user_id,
            tier=subscription.plan.tier,
            status=subscription.status,
            is_active=subscription.is_active,
            billing_cycle=subscription.billing_cycle,
            next_billing_date=subscription.next_billing_date,
            is_trial=subscription.is_trial,
            trial_ends_at=subscription.trial_ends_at,
            created_at=subscription.created_at,
            usage={
                "requests_current_day": subscription.usage.requests_current_day,
                "requests_current_month": subscription.usage.requests_current_month,
                "tokens_current_day": subscription.usage.tokens_current_day,
                "tokens_current_month": subscription.usage.tokens_current_month,
                "active_sessions": subscription.usage.active_sessions,
                "usage_by_graph": subscription.usage.usage_by_graph,
            },
            limits={
                "requests_per_day": subscription.plan.limits.requests_per_day,
                "requests_per_month": subscription.plan.limits.requests_per_month,
                "tokens_per_day": subscription.plan.limits.tokens_per_day,
                "tokens_per_month": subscription.plan.limits.tokens_per_month,
                "max_concurrent_sessions": subscription.plan.limits.max_concurrent_sessions,
                "allowed_graphs": [
                    g.value for g in subscription.plan.limits.allowed_graphs
                ],
            },
        )


class BillingEvent(BaseModel):
    """
    Billing event model.

    Represents billing-related events.
    """

    event_id: str = Field(..., description="Event ID")
    user_id: UUID = Field(..., description="User ID")
    subscription_id: UUID = Field(..., description="Subscription ID")
    event_type: str = Field(..., description="Event type")
    amount: float = Field(..., description="Event amount")
    currency: str = Field("USD", description="Currency")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")
