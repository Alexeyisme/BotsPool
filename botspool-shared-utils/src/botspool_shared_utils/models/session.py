"""Session-related models for BotsPool."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import Field, validator

from .base import BaseModel
from .enums import FrontendType


class SessionBase(BaseModel):
    """Shared fields for durable session records."""

    frontend_type: FrontendType = Field(
        ..., description="Frontend source for the session"
    )
    chat_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Frontend-specific chat/conversation identifier",
    )
    user_id: Optional[UUID] = Field(
        None, description="Associated BotsPool user identifier, if known"
    )
    current_agent: Optional[str] = Field(
        None, max_length=100, description="Active agent routed within the session"
    )
    locale: Optional[str] = Field(
        None, max_length=10, description="Preferred locale for responses"
    )
    state_payload: Dict[str, Any] = Field(
        default_factory=dict, description="Auxiliary state captured for the session"
    )
    expires_at: Optional[datetime] = Field(
        None, description="Optional expiration timestamp for the session"
    )

    @validator("chat_id")
    def validate_chat_id(cls, value: str) -> str:
        """Ensure chat identifiers are normalised and non-empty."""
        normalised = value.strip()
        if not normalised:
            raise ValueError("chat_id must not be empty")
        return normalised


class SessionCreate(SessionBase):
    """Payload used when creating a new session record."""

    pass


class SessionUpdate(BaseModel):
    """Partial update payload for existing sessions."""

    user_id: Optional[UUID] = Field(
        None, description="Updated BotsPool user identifier"
    )
    current_agent: Optional[str] = Field(
        None, max_length=100, description="Updated agent binding"
    )
    locale: Optional[str] = Field(
        None, max_length=10, description="Updated locale preference"
    )
    state_payload: Optional[Dict[str, Any]] = Field(
        None, description="Replacement payload for session state"
    )
    expires_at: Optional[datetime] = Field(
        None, description="Updated expiration timestamp"
    )
    last_activity_at: Optional[datetime] = Field(
        None, description="Override for last activity timestamp"
    )


class SessionRecord(SessionBase):
    """Full durable session representation returned by the service layer."""

    id: UUID = Field(..., description="Unique session record identifier")
    last_activity_at: datetime = Field(
        ..., description="Timestamp of the last tracked activity"
    )
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")
