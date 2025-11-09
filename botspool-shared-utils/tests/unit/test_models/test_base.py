"""
Unit tests for base models and mixins
"""

import pytest
from datetime import datetime
from uuid import UUID
from botspool_shared_utils.models.base import (
    BaseModel,
    TimestampMixin,
    MetadataMixin,
    BaseEntity,
)


class TestTimestampMixin:
    """Test TimestampMixin functionality."""

    def test_timestamp_mixin_creation(self):
        """Test that TimestampMixin adds timestamp fields."""

        class TestModel(TimestampMixin):
            name: str

        model = TestModel(name="test")

        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")
        assert isinstance(model.created_at, datetime)
        assert isinstance(model.updated_at, datetime)

    def test_timestamp_mixin_default_values(self):
        """Test that timestamp fields have default values."""

        class TestModel(TimestampMixin):
            name: str

        model = TestModel(name="test")

        # Timestamps should be close to current time
        now = datetime.utcnow()
        assert abs((model.created_at - now).total_seconds()) < 1
        assert abs((model.updated_at - now).total_seconds()) < 1


class TestMetadataMixin:
    """Test MetadataMixin functionality."""

    def test_metadata_mixin_creation(self):
        """Test that MetadataMixin adds metadata field."""

        class TestModel(MetadataMixin):
            name: str

        model = TestModel(name="test")

        assert hasattr(model, "metadata")
        assert isinstance(model.metadata, dict)
        assert model.metadata == {}

    def test_metadata_mixin_custom_metadata(self):
        """Test that metadata can be customized."""

        class TestModel(MetadataMixin):
            name: str

        custom_metadata = {"key1": "value1", "key2": 123}
        model = TestModel(name="test", metadata=custom_metadata)

        assert model.metadata == custom_metadata


class TestBaseEntity:
    """Test BaseEntity functionality."""

    def test_base_entity_creation(self):
        """Test that BaseEntity combines all mixins."""

        class TestEntity(BaseEntity):
            name: str

        entity = TestEntity(name="test")

        # Should have all mixin fields
        assert hasattr(entity, "id")
        assert hasattr(entity, "created_at")
        assert hasattr(entity, "updated_at")
        assert hasattr(entity, "metadata")

        # Should have proper types
        assert isinstance(entity.id, UUID)
        assert isinstance(entity.created_at, datetime)
        assert isinstance(entity.updated_at, datetime)
        assert isinstance(entity.metadata, dict)

    def test_base_entity_id_generation(self):
        """Test that BaseEntity generates unique IDs."""

        class TestEntity(BaseEntity):
            name: str

        entity1 = TestEntity(name="test1")
        entity2 = TestEntity(name="test2")

        assert entity1.id != entity2.id
        assert str(entity1.id) != ""
        assert str(entity2.id) != ""

    def test_base_entity_serialization(self):
        """Test that BaseEntity can be serialized."""

        class TestEntity(BaseEntity):
            name: str

        entity = TestEntity(name="test")
        data = entity.model_dump()

        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "metadata" in data
        assert data["name"] == "test"

    def test_base_entity_deserialization(self):
        """Test that BaseEntity can be deserialized."""

        class TestEntity(BaseEntity):
            name: str

        test_uuid = "550e8400-e29b-41d4-a716-446655440000"
        data = {
            "id": test_uuid,
            "name": "test",
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:00:00Z",
            "metadata": {"key": "value"},
        }

        entity = TestEntity.model_validate(data)

        assert str(entity.id) == test_uuid
        assert entity.name == "test"
        assert entity.metadata == {"key": "value"}


class TestBaseModel:
    """Test BaseModel functionality."""

    def test_base_model_creation(self):
        """Test that BaseModel works as expected."""

        class TestModel(BaseModel):
            name: str
            value: int

        model = TestModel(name="test", value=42)

        assert model.name == "test"
        assert model.value == 42

    def test_base_model_validation(self):
        """Test that BaseModel validates input."""

        class TestModel(BaseModel):
            name: str
            value: int

        # Valid data should work
        model = TestModel(name="test", value=42)
        assert model.name == "test"

        # Invalid data should raise validation error
        with pytest.raises(ValueError):
            TestModel(name="test", value="not_a_number")

    def test_base_model_serialization(self):
        """Test that BaseModel can be serialized."""

        class TestModel(BaseModel):
            name: str
            value: int

        model = TestModel(name="test", value=42)
        data = model.model_dump()

        assert data == {"name": "test", "value": 42}

    def test_base_model_deserialization(self):
        """Test that BaseModel can be deserialized."""

        class TestModel(BaseModel):
            name: str
            value: int

        data = {"name": "test", "value": 42}
        model = TestModel.model_validate(data)

        assert model.name == "test"
        assert model.value == 42
