"""
Base models and mixins for BotsPool

This module provides base classes and mixins that are used across all models
to ensure consistency and reduce code duplication.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel as PydanticBaseModel, Field, validator


class BaseModel(PydanticBaseModel):
    """
    Base model class with common configuration for all BotsPool models.

    Provides:
    - JSON serialization with camelCase for API responses
    - Validation configuration
    - Common field patterns
    """

    class Config:
        # Use camelCase for JSON field names (API compatibility)
        alias_generator = lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        )
        populate_by_name = True  # Updated for Pydantic V2
        validate_assignment = True
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class TimestampMixin(BaseModel):
    """
    Mixin that adds created_at and updated_at timestamp fields.

    Used by models that need to track when records were created and last modified.
    """

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record last update timestamp"
    )

    @validator("updated_at", pre=True, always=True)
    def update_timestamp(cls, v, values):
        """Automatically update the updated_at field when any field changes."""
        return datetime.utcnow()


class MetadataMixin(BaseModel):
    """
    Mixin that adds metadata field for storing additional information.

    Used by models that need to store flexible, schema-less data.
    """

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class IdentifiableMixin(BaseModel):
    """
    Mixin that adds an ID field with UUID generation.

    Used by models that need unique identifiers.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")


class VersionedMixin(BaseModel):
    """
    Mixin that adds version tracking for optimistic locking.

    Used by models that need to handle concurrent updates.
    """

    version: int = Field(
        default=1, ge=1, description="Record version for optimistic locking"
    )


class SoftDeleteMixin(BaseModel):
    """
    Mixin that adds soft delete functionality.

    Used by models that need to support soft deletion instead of hard deletion.
    """

    deleted_at: Optional[datetime] = Field(None, description="Soft deletion timestamp")
    is_deleted: bool = Field(False, description="Soft deletion flag")

    def soft_delete(self) -> None:
        """Mark the record as deleted."""
        self.deleted_at = datetime.utcnow()
        self.is_deleted = True

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.is_deleted = False


class BaseEntity(IdentifiableMixin, TimestampMixin, MetadataMixin):
    """
    Base entity class combining common mixins.

    This is the most commonly used base class for main entities in the system.
    """

    pass


class BaseAuditableEntity(BaseEntity, VersionedMixin, SoftDeleteMixin):
    """
    Base auditable entity class with full audit capabilities.

    Used for entities that need complete audit trails and soft deletion.
    """

    pass
