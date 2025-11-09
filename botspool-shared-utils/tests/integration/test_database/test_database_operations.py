"""
Integration tests for database operations using SQLAlchemy ORM models
"""

import pytest
import pytest_asyncio
import time
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from botspool_shared_utils.database.models import (
    UserModel,
    UserAuthModel,
    UserProfileModel,
    ChatSessionModel,
    ChatMessageModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    UsageTrackingModel,
    GraphModel,
)
from botspool_shared_utils.models.enums import (
    UserRole,
    SubscriptionTier,
    GraphType,
    ChatMessageType,
    AuthProvider,
    FrontendType,
    ChatStatus,
    GraphStatus,
    MessageType,
)


def get_unique_identifier():
    """Generate a unique identifier for test data to avoid UNIQUE constraint violations."""
    return str(int(time.time() * 1000000))  # Microsecond precision


class TestUserDatabaseOperations:
    """Test user database operations."""

    @pytest.mark.asyncio
    async def test_create_user(self, test_database_session: AsyncSession):
        """Test creating a user in the database."""
        unique_id = get_unique_identifier()

        # Create user model
        user = UserModel(
            role=UserRole.USER, subscription_tier=SubscriptionTier.FREE, is_active=True
        )

        test_database_session.add(user)
        await test_database_session.flush()  # Get the user ID

        # Create auth model
        auth = UserAuthModel(
            user_id=user.id,
            provider=AuthProvider.EMAIL,
            email=f"test_{unique_id}@example.com",
            password_hash="hashed_password",
            is_verified=True,
        )

        # Create profile model
        profile = UserProfileModel(user_id=user.id, username=f"testuser_{unique_id}")

        test_database_session.add(auth)
        test_database_session.add(profile)
        await test_database_session.commit()
        await test_database_session.refresh(user)

        assert user.id is not None
        assert auth.email == f"test_{unique_id}@example.com"
        assert profile.username == f"testuser_{unique_id}"
        assert user.is_active is True
        assert auth.is_verified is True
        assert user.role == UserRole.USER
        assert user.subscription_tier == SubscriptionTier.FREE

    @pytest.mark.asyncio
    async def test_retrieve_user(self, test_database_session: AsyncSession):
        """Test retrieving a user from the database."""
        unique_id = get_unique_identifier()

        # Create user model
        user = UserModel(
            role=UserRole.USER, subscription_tier=SubscriptionTier.FREE, is_active=True
        )

        test_database_session.add(user)
        await test_database_session.flush()

        # Create auth and profile models
        auth = UserAuthModel(
            user_id=user.id,
            provider=AuthProvider.EMAIL,
            email=f"retrieve_{unique_id}@example.com",
            password_hash="hashed_password",
            is_verified=True,
        )

        profile = UserProfileModel(
            user_id=user.id, username=f"retrieveuser_{unique_id}"
        )

        test_database_session.add(auth)
        test_database_session.add(profile)
        await test_database_session.commit()

        # Retrieve the user
        result = await test_database_session.execute(
            select(UserModel).where(UserModel.id == user.id)
        )
        retrieved_user = result.scalar_one_or_none()

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.is_active is True

        # Verify auth and profile records separately to avoid relationship loading issues
        auth_result = await test_database_session.execute(
            select(UserAuthModel).where(UserAuthModel.user_id == user.id)
        )
        auth_record = auth_result.scalar_one_or_none()
        assert auth_record is not None
        assert auth_record.email == f"retrieve_{unique_id}@example.com"

        profile_result = await test_database_session.execute(
            select(UserProfileModel).where(UserProfileModel.user_id == user.id)
        )
        profile_record = profile_result.scalar_one_or_none()
        assert profile_record is not None
        assert profile_record.username == f"retrieveuser_{unique_id}"

    @pytest.mark.asyncio
    async def test_update_user(self, test_database_session: AsyncSession):
        """Test updating a user in the database."""
        unique_id = get_unique_identifier()

        # Create user model
        user = UserModel(
            role=UserRole.USER, subscription_tier=SubscriptionTier.FREE, is_active=True
        )

        test_database_session.add(user)
        await test_database_session.flush()

        # Create auth and profile models
        auth = UserAuthModel(
            user_id=user.id,
            provider=AuthProvider.EMAIL,
            email=f"update_{unique_id}@example.com",
            password_hash="hashed_password",
            is_verified=True,
        )

        profile = UserProfileModel(user_id=user.id, username=f"updateuser_{unique_id}")

        test_database_session.add(auth)
        test_database_session.add(profile)
        await test_database_session.commit()

        # Update the user
        user.is_active = False
        user.subscription_tier = SubscriptionTier.PREMIUM
        profile.display_name = "Updated User"

        await test_database_session.commit()
        await test_database_session.refresh(user)

        assert user.is_active is False
        assert user.subscription_tier == SubscriptionTier.PREMIUM

        # Verify profile update separately to avoid relationship loading issues
        profile_result = await test_database_session.execute(
            select(UserProfileModel).where(UserProfileModel.user_id == user.id)
        )
        profile_record = profile_result.scalar_one_or_none()
        assert profile_record is not None
        assert profile_record.display_name == "Updated User"

    @pytest.mark.asyncio
    async def test_delete_user(self, test_database_session: AsyncSession):
        """Test deleting a user from the database."""
        unique_id = get_unique_identifier()

        # Create user model
        user = UserModel(
            role=UserRole.USER, subscription_tier=SubscriptionTier.FREE, is_active=True
        )

        test_database_session.add(user)
        await test_database_session.flush()

        # Create auth and profile models
        auth = UserAuthModel(
            user_id=user.id,
            provider=AuthProvider.EMAIL,
            email=f"delete_{unique_id}@example.com",
            password_hash="hashed_password",
            is_verified=True,
        )

        profile = UserProfileModel(user_id=user.id, username=f"deleteuser_{unique_id}")

        test_database_session.add(auth)
        test_database_session.add(profile)
        await test_database_session.commit()

        # Delete related records first to avoid foreign key constraints
        # Delete auth records
        auth_records = await test_database_session.execute(
            select(UserAuthModel).where(UserAuthModel.user_id == user.id)
        )
        for auth_record in auth_records.scalars():
            await test_database_session.delete(auth_record)

        # Delete profile records
        profile_records = await test_database_session.execute(
            select(UserProfileModel).where(UserProfileModel.user_id == user.id)
        )
        for profile_record in profile_records.scalars():
            await test_database_session.delete(profile_record)

        # Then delete the user
        await test_database_session.delete(user)
        await test_database_session.commit()

        # Verify deletion
        result = await test_database_session.execute(
            select(UserModel).where(UserModel.id == user.id)
        )
        deleted_user = result.scalar_one_or_none()

        assert deleted_user is None


class TestChatDatabaseOperations:
    """Test chat database operations."""

    @pytest.mark.asyncio
    async def test_create_chat_session(
        self, test_database_session: AsyncSession, sample_user_in_db
    ):
        """Test creating a chat session in the database."""
        unique_id = get_unique_identifier()

        chat = ChatSessionModel(
            user_id=sample_user_in_db.id,
            session_id=f"test_chat_session_{unique_id}",
            frontend_type=FrontendType.WEB,
            status=ChatStatus.ACTIVE,
            title="Test Chat Session",
            current_graph=GraphType.TODO,
        )

        test_database_session.add(chat)
        await test_database_session.commit()
        await test_database_session.refresh(chat)

        assert chat.id is not None
        assert chat.user_id == sample_user_in_db.id
        assert chat.session_id == f"test_chat_session_{unique_id}"
        assert chat.frontend_type == FrontendType.WEB
        assert chat.status == ChatStatus.ACTIVE
        assert chat.title == "Test Chat Session"
        assert chat.current_graph == GraphType.TODO

    @pytest.mark.asyncio
    async def test_add_message_to_chat(
        self, test_database_session: AsyncSession, sample_chat_in_db
    ):
        """Test adding a message to a chat session."""
        message = ChatMessageModel(
            session_id=sample_chat_in_db.id,
            user_id=sample_chat_in_db.user_id,
            message_type=MessageType.USER,
            content="Hello, this is a test message",
            graph_type=GraphType.TODO,
        )

        test_database_session.add(message)
        await test_database_session.commit()
        await test_database_session.refresh(message)

        assert message.id is not None
        assert message.session_id == sample_chat_in_db.id
        assert message.user_id == sample_chat_in_db.user_id
        assert message.message_type == MessageType.USER
        assert message.content == "Hello, this is a test message"
        assert message.graph_type == GraphType.TODO


class TestSubscriptionDatabaseOperations:
    """Test subscription database operations."""

    @pytest.mark.asyncio
    async def test_create_subscription(
        self, test_database_session: AsyncSession, sample_user_in_db
    ):
        """Test creating a subscription in the database."""
        unique_id = get_unique_identifier()

        # Use a unique subscription tier to avoid UNIQUE constraint violation
        # Since tier has unique=True, we need to use different tiers
        # Use a more deterministic approach to avoid conflicts
        tier_index = hash(unique_id) % 4
        tiers = [
            SubscriptionTier.FREE,
            SubscriptionTier.BASIC,
            SubscriptionTier.PREMIUM,
            SubscriptionTier.ENTERPRISE,
        ]
        tier = tiers[tier_index]

        # Check if plan already exists and delete it first
        existing_plan = await test_database_session.execute(
            select(SubscriptionPlanModel).where(SubscriptionPlanModel.tier == tier)
        )
        existing_plan_obj = existing_plan.scalar_one_or_none()
        if existing_plan_obj:
            # Delete related subscriptions first to avoid foreign key constraints
            related_subscriptions = await test_database_session.execute(
                select(SubscriptionModel).where(
                    SubscriptionModel.plan_id == existing_plan_obj.id
                )
            )
            for subscription in related_subscriptions.scalars():
                await test_database_session.delete(subscription)

            # Then delete the plan
            await test_database_session.delete(existing_plan_obj)
            await test_database_session.flush()

        # First create a subscription plan
        plan = SubscriptionPlanModel(
            tier=tier,
            name=f"Test Plan {unique_id}",
            description=f"Test subscription plan {unique_id}",
            price_monthly=2999,  # $29.99 in cents
            price_yearly=29999,  # $299.99 in cents
            limits={"requests_per_month": 10000, "graphs": ["todo", "research"]},
        )

        test_database_session.add(plan)
        await test_database_session.flush()

        # Create usage tracking
        usage = UsageTrackingModel(user_id=sample_user_in_db.id, subscription_tier=tier)

        test_database_session.add(usage)
        await test_database_session.flush()

        # Create subscription
        subscription = SubscriptionModel(
            user_id=sample_user_in_db.id,
            plan_id=plan.id,
            next_billing_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )

        test_database_session.add(subscription)
        await test_database_session.commit()
        await test_database_session.refresh(subscription)

        assert subscription.id is not None
        assert subscription.user_id == sample_user_in_db.id
        assert subscription.plan_id == plan.id
        assert subscription.is_active is True
        assert subscription.status == "active"


class TestGraphDatabaseOperations:
    """Test graph database operations."""

    @pytest.mark.asyncio
    async def test_create_graph(self, test_database_session: AsyncSession):
        """Test creating a graph in the database."""
        unique_id = get_unique_identifier()

        # Use a unique graph type to avoid UNIQUE constraint violation
        # Since graph_type has unique=True, we need to use different types
        graph_types = [
            GraphType.TODO,
            GraphType.RESEARCH,
            GraphType.EMAIL,
            GraphType.CALENDAR,
            GraphType.DOCUMENT,
            GraphType.CODE,
        ]
        graph_type = graph_types[int(unique_id) % len(graph_types)]

        # Check if graph already exists and delete it first
        existing_graph = await test_database_session.execute(
            select(GraphModel).where(GraphModel.graph_type == graph_type)
        )
        existing_graph_obj = existing_graph.scalar_one_or_none()
        if existing_graph_obj:
            await test_database_session.delete(existing_graph_obj)
            await test_database_session.flush()

        graph = GraphModel(
            graph_type=graph_type,
            name=f"Test Graph {unique_id}",
            description="A test graph for integration testing",
            version="1.0.0",
            author="Test Author",
            status=GraphStatus.HEALTHY,
            is_available=True,
            default_config={"model_name": "gpt-3.5-turbo", "model_version": "1.0"},
        )

        test_database_session.add(graph)
        await test_database_session.commit()
        await test_database_session.refresh(graph)

        assert graph.id is not None
        assert graph.graph_type == graph_type
        assert graph.name == f"Test Graph {unique_id}"
        assert graph.description == "A test graph for integration testing"
        assert graph.version == "1.0.0"
        assert graph.author == "Test Author"
        assert graph.status == GraphStatus.HEALTHY
        assert graph.is_available is True
        assert graph.default_config["model_name"] == "gpt-3.5-turbo"


class TestDatabaseTransactions:
    """Test database transaction operations."""

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, test_database_session: AsyncSession):
        """Test transaction rollback functionality."""
        unique_id = get_unique_identifier()

        # Create a user
        user = UserModel(
            role=UserRole.USER, subscription_tier=SubscriptionTier.FREE, is_active=True
        )

        test_database_session.add(user)
        await test_database_session.flush()

        # Create auth model
        auth = UserAuthModel(
            user_id=user.id,
            provider=AuthProvider.EMAIL,
            email=f"rollback_{unique_id}@example.com",
            password_hash="hashed_password",
            is_verified=True,
        )

        test_database_session.add(auth)
        # Don't commit - just flush to get IDs

        # Store user ID before rollback to avoid accessing it after
        user_id = user.id

        # Verify user exists in current transaction
        result = await test_database_session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        assert result.scalar_one_or_none() is not None

        # Rollback the transaction
        await test_database_session.rollback()

        # Verify user no longer exists (rollback worked)
        # Use the stored user_id to avoid accessing user.id after rollback
        result = await test_database_session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_transaction_commit(self, test_database_session: AsyncSession):
        """Test transaction commit functionality."""
        unique_id = get_unique_identifier()

        # Create a user
        user = UserModel(
            role=UserRole.USER, subscription_tier=SubscriptionTier.FREE, is_active=True
        )

        test_database_session.add(user)
        await test_database_session.flush()

        # Create auth model
        auth = UserAuthModel(
            user_id=user.id,
            provider=AuthProvider.EMAIL,
            email=f"commit_{unique_id}@example.com",
            password_hash="hashed_password",
            is_verified=True,
        )

        test_database_session.add(auth)
        await test_database_session.commit()

        # Verify user exists after commit
        result = await test_database_session.execute(
            select(UserModel).where(UserModel.id == user.id)
        )
        committed_user = result.scalar_one_or_none()

        assert committed_user is not None

        # Verify auth record exists separately to avoid relationship loading issues
        auth_result = await test_database_session.execute(
            select(UserAuthModel).where(UserAuthModel.user_id == user.id)
        )
        auth_record = auth_result.scalar_one_or_none()
        assert auth_record is not None
        assert auth_record.email == f"commit_{unique_id}@example.com"
