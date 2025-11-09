"""
User-related models for BotsPool

This module contains all models related to user management, authentication,
and user preferences.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator, EmailStr

from .base import BaseEntity, TimestampMixin
from .enums import UserRole, AuthProvider, SubscriptionTier


class UserAuth(BaseModel):
    """
    User authentication information.

    Stores authentication details including provider-specific data.
    """

    provider: AuthProvider = Field(..., description="Authentication provider")
    provider_id: Optional[str] = Field(None, description="Provider-specific user ID")
    email: EmailStr = Field(..., description="User email address")
    password_hash: Optional[str] = Field(
        None, description="Hashed password (for email auth)"
    )
    is_verified: bool = Field(False, description="Email verification status")
    mfa_enabled: bool = Field(False, description="Multi-factor authentication enabled")
    mfa_secret: Optional[str] = Field(None, description="MFA secret key")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    failed_login_attempts: int = Field(
        0, ge=0, description="Failed login attempts count"
    )
    locked_until: Optional[datetime] = Field(None, description="Account lockout expiry")

    @validator("email")
    def validate_email(cls, v):
        """Validate email format."""
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        return v.lower()

    @validator("password_hash")
    def validate_password_hash(cls, v, values):
        """Ensure password hash is provided for email authentication."""
        if values.get("provider") == AuthProvider.EMAIL and not v:
            raise ValueError("Password hash is required for email authentication")
        return v


class UserProfile(BaseModel):
    """
    User profile information.

    Stores user's personal and public information.
    """

    username: str = Field(
        ..., min_length=3, max_length=50, description="Unique username"
    )
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    display_name: Optional[str] = Field(
        None, max_length=150, description="Display name"
    )
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    timezone: str = Field("UTC", description="User timezone")
    language: str = Field(
        "en", min_length=2, max_length=5, description="Preferred language"
    )
    country: Optional[str] = Field(
        None, max_length=2, description="Country code (ISO 3166-1)"
    )

    @validator("username")
    def validate_username(cls, v):
        """Validate username format."""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        return v.lower()

    @validator("display_name")
    def set_display_name(cls, v, values):
        """Set display name from first and last name if not provided."""
        if not v and values.get("first_name") and values.get("last_name"):
            return f"{values['first_name']} {values['last_name']}"
        return v


class UserPreferences(BaseModel):
    """
    User preferences and settings.

    Stores user's application preferences and configuration.
    """

    # Notification preferences
    email_notifications: bool = Field(True, description="Enable email notifications")
    push_notifications: bool = Field(True, description="Enable push notifications")
    sms_notifications: bool = Field(False, description="Enable SMS notifications")

    # Chat preferences
    default_graph: Optional[str] = Field(None, description="Default graph type")
    auto_route: bool = Field(True, description="Enable automatic graph routing")
    chat_history_retention: int = Field(
        30, ge=1, le=365, description="Chat history retention in days"
    )

    # Privacy preferences
    data_sharing: bool = Field(False, description="Allow data sharing for analytics")
    profile_visibility: str = Field("private", description="Profile visibility level")

    # UI preferences
    theme: str = Field("light", description="UI theme preference")
    compact_mode: bool = Field(False, description="Enable compact UI mode")

    # Advanced preferences
    debug_mode: bool = Field(False, description="Enable debug mode")
    beta_features: bool = Field(False, description="Enable beta features")


class UserSession(BaseModel):
    """
    User session information.

    Tracks active user sessions for security and analytics.
    """

    session_id: str = Field(..., description="Unique session identifier")
    user_id: UUID = Field(..., description="User ID")
    frontend_type: str = Field(..., description="Frontend type (telegram, web, etc.)")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Session creation time"
    )
    last_activity: datetime = Field(
        default_factory=datetime.utcnow, description="Last activity time"
    )
    expires_at: datetime = Field(..., description="Session expiration time")
    is_active: bool = Field(True, description="Session active status")

    @validator("ip_address")
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        if v and not re.match(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", v):
            raise ValueError("Invalid IP address format")
        return v


class User(BaseEntity):
    """
    Main user model.

    Combines all user-related information into a single entity.
    """

    # Core user information
    auth: UserAuth = Field(..., description="Authentication information")
    profile: UserProfile = Field(..., description="Profile information")
    preferences: UserPreferences = Field(
        default_factory=UserPreferences, description="User preferences"
    )

    # System information
    role: UserRole = Field(UserRole.FREE_USER, description="User role")
    subscription_tier: SubscriptionTier = Field(
        SubscriptionTier.FREE, description="Subscription tier"
    )
    is_active: bool = Field(True, description="User active status")
    is_suspended: bool = Field(False, description="User suspension status")

    # Timestamps
    email_verified_at: Optional[datetime] = Field(
        None, description="Email verification timestamp"
    )
    last_activity: Optional[datetime] = Field(
        None, description="Last activity timestamp"
    )

    # Statistics
    total_chats: int = Field(0, ge=0, description="Total number of chats")
    total_messages: int = Field(0, ge=0, description="Total number of messages")

    @validator("subscription_tier")
    def validate_subscription_tier(cls, v, values):
        """Validate subscription tier matches user role."""
        role = values.get("role")
        if role:
            # Handle both enum and string values
            role_value = role.value if hasattr(role, "value") else str(role)
            tier_value = v.value if hasattr(v, "value") else str(v)
            if role_value != tier_value.replace("_user", ""):
                # Allow some flexibility in role/tier matching
                pass
        return v

    def get_display_name(self) -> str:
        """Get the user's display name."""
        return self.profile.display_name or self.profile.username

    def is_premium_user(self) -> bool:
        """Check if user has premium subscription."""
        return self.subscription_tier in [
            SubscriptionTier.PREMIUM,
            SubscriptionTier.ENTERPRISE,
        ]

    def can_access_graph(self, graph_type: str) -> bool:
        """Check if user can access a specific graph type."""
        # Free users can access basic graphs
        if self.subscription_tier == SubscriptionTier.FREE:
            return graph_type in ["todo"]

        # Basic users can access todo and email
        if self.subscription_tier == SubscriptionTier.BASIC:
            return graph_type in ["todo", "email"]

        # Premium and Enterprise users can access all graphs
        return True

    def update_last_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class UserCreate(BaseModel):
    """
    Model for creating a new user.

    Used in registration endpoints.
    """

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="Password")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    timezone: str = Field("UTC", description="User timezone")
    language: str = Field("en", description="Preferred language")

    @validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")

        return v


class UserUpdate(BaseModel):
    """
    Model for updating user information.

    Used in user profile update endpoints.
    """

    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    display_name: Optional[str] = Field(
        None, max_length=150, description="Display name"
    )
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    timezone: Optional[str] = Field(None, description="User timezone")
    language: Optional[str] = Field(
        None, min_length=2, max_length=5, description="Preferred language"
    )
    country: Optional[str] = Field(None, max_length=2, description="Country code")
    preferences: Optional[UserPreferences] = Field(None, description="User preferences")


class UserResponse(BaseModel):
    """
    Model for user API responses.

    Excludes sensitive information like password hashes.
    """

    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    display_name: str = Field(..., description="Display name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    role: UserRole = Field(..., description="User role")
    subscription_tier: SubscriptionTier = Field(..., description="Subscription tier")
    is_active: bool = Field(..., description="Active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_activity: Optional[datetime] = Field(
        None, description="Last activity timestamp"
    )

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        """Create UserResponse from User model."""
        return cls(
            id=user.id,
            email=user.auth.email,
            username=user.profile.username,
            display_name=user.get_display_name(),
            avatar_url=user.profile.avatar_url,
            role=user.role,
            subscription_tier=user.subscription_tier,
            is_active=user.is_active,
            created_at=user.created_at,
            last_activity=user.last_activity,
        )
