"""
Integration test configuration and fixtures for botspool-shared-utils
"""

import asyncio
import pytest
import pytest_asyncio
import os
import tempfile
import time
from typing import AsyncGenerator, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import redis.asyncio as redis


def get_unique_identifier():
    """Generate a unique identifier for test data to avoid UNIQUE constraint violations."""
    return str(int(time.time() * 1000000))  # Microsecond precision


# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///test_integration.db"
TEST_REDIS_URL = "redis://localhost:6379/14"  # Use different test database


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_database_engine():
    """Create test database engine."""
    from botspool_shared_utils.database.models import Base

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_redis_client():
    """Create test Redis client."""
    client = redis.from_url(TEST_REDIS_URL, decode_responses=True)
    yield client
    await client.close()


@pytest_asyncio.fixture
async def test_database_session(
    test_database_engine,
) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        test_database_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def clean_redis(test_redis_client):
    """Clean Redis test database before each test."""
    await test_redis_client.flushdb()
    yield test_redis_client
    await test_redis_client.flushdb()


@pytest.fixture
def temp_config_file():
    """Temporary configuration file for integration testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as f:
        f.write(f"DATABASE_URL={TEST_DATABASE_URL}\n")
        f.write(f"REDIS_URL={TEST_REDIS_URL}\n")
        f.write("JWT_PRIVATE_KEY=test_private_key\n")
        f.write("JWT_PUBLIC_KEY=test_public_key\n")
        f.write("ENCRYPTION_KEY=test_encryption_key_32_bytes_long\n")
        temp_file = f.name

    yield temp_file

    # Cleanup
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest_asyncio.fixture
async def sample_user_in_db(test_database_session):
    """Create a sample user in the test database."""
    from botspool_shared_utils.database.models import (
        UserModel,
        UserAuthModel,
        UserProfileModel,
    )
    from botspool_shared_utils.models.enums import (
        UserRole,
        SubscriptionTier,
        AuthProvider,
    )

    # Create SQLAlchemy models directly
    user_model = UserModel(
        role=UserRole.USER, subscription_tier=SubscriptionTier.FREE, is_active=True
    )

    test_database_session.add(user_model)
    await test_database_session.flush()  # Get the user ID

    # Create auth model with unique email
    unique_id = get_unique_identifier()
    auth_model = UserAuthModel(
        user_id=user_model.id,
        provider=AuthProvider.EMAIL,
        email=f"integration_{unique_id}@example.com",
        password_hash="hashed_password",
        is_verified=True,
    )

    # Create profile model with unique username
    profile_model = UserProfileModel(
        user_id=user_model.id, username=f"integration_user_{unique_id}"
    )

    test_database_session.add(auth_model)
    test_database_session.add(profile_model)
    await test_database_session.commit()
    await test_database_session.refresh(user_model)

    yield user_model

    # Cleanup - delete in proper order to avoid foreign key constraints
    try:
        # Delete related records first
        await test_database_session.execute(
            select(UserAuthModel).where(UserAuthModel.user_id == user_model.id)
        )
        auth_records = await test_database_session.execute(
            select(UserAuthModel).where(UserAuthModel.user_id == user_model.id)
        )
        for auth_record in auth_records.scalars():
            await test_database_session.delete(auth_record)

        profile_records = await test_database_session.execute(
            select(UserProfileModel).where(UserProfileModel.user_id == user_model.id)
        )
        for profile_record in profile_records.scalars():
            await test_database_session.delete(profile_record)

        # Then delete the user
        await test_database_session.delete(user_model)
        await test_database_session.commit()
    except Exception:
        await test_database_session.rollback()


@pytest_asyncio.fixture
async def sample_chat_in_db(test_database_session, sample_user_in_db):
    """Create a sample chat in the test database."""
    from botspool_shared_utils.database.models import ChatSessionModel
    from botspool_shared_utils.models.enums import GraphType, FrontendType, ChatStatus

    unique_id = get_unique_identifier()
    chat_model = ChatSessionModel(
        user_id=sample_user_in_db.id,
        session_id=f"test_session_{unique_id}",
        frontend_type=FrontendType.WEB,
        status=ChatStatus.ACTIVE,
        title="Test Chat Session",
        current_graph=GraphType.TODO,
    )

    test_database_session.add(chat_model)
    await test_database_session.commit()
    await test_database_session.refresh(chat_model)

    yield chat_model

    # Cleanup - delete in proper order to avoid foreign key constraints
    try:
        # Delete related chat messages first
        from botspool_shared_utils.database.models import ChatMessageModel

        message_records = await test_database_session.execute(
            select(ChatMessageModel).where(ChatMessageModel.session_id == chat_model.id)
        )
        for message_record in message_records.scalars():
            await test_database_session.delete(message_record)

        # Then delete the chat session
        await test_database_session.delete(chat_model)
        await test_database_session.commit()
    except Exception:
        await test_database_session.rollback()


@pytest_asyncio.fixture
async def sample_subscription_in_db(test_database_session, sample_user_in_db):
    """Create a sample subscription in the test database."""
    from botspool_shared_utils.models.subscription import Subscription
    from botspool_shared_utils.models.enums import SubscriptionTier

    subscription = Subscription(
        user_id=sample_user_in_db.id,
        plan_id="test-plan",
        current_tier=SubscriptionTier.BASIC,
        is_active=True,
    )

    test_database_session.add(subscription)
    await test_database_session.commit()
    await test_database_session.refresh(subscription)

    yield subscription

    # Cleanup
    await test_database_session.delete(subscription)
    await test_database_session.commit()


@pytest_asyncio.fixture
async def sample_graph_in_db(test_database_session):
    """Create a sample graph in the test database."""
    from botspool_shared_utils.models.graph import Graph, GraphConfig
    from botspool_shared_utils.models.enums import GraphType

    graph = Graph(
        name="Test Graph",
        graph_type=GraphType.TODO,
        description="Test graph for integration testing",
        version="1.0.0",
        author="Test Author",
        default_config=GraphConfig(model_name="gpt-3.5-turbo", model_version="1.0"),
    )

    test_database_session.add(graph)
    await test_database_session.commit()
    await test_database_session.refresh(graph)

    yield graph

    # Cleanup
    await test_database_session.delete(graph)
    await test_database_session.commit()


@pytest_asyncio.fixture
async def sample_redis_data(clean_redis):
    """Create sample data in Redis."""
    # Create sample session data
    await clean_redis.hset(
        "session:test-session",
        mapping={
            "user_id": "test-user",
            "created_at": "2024-01-01T10:00:00Z",
            "expires_at": "2024-01-01T11:00:00Z",
            "is_active": "true",
        },
    )

    # Create sample pool registry data
    await clean_redis.sadd("pool:todo", "instance-1", "instance-2")

    # Create sample usage tracking data
    await clean_redis.hset(
        "usage:test-user:2024-01",
        mapping={
            "api_calls": "100",
            "concurrent_sessions": "2",
            "last_updated": "2024-01-01T10:00:00Z",
        },
    )

    yield clean_redis
