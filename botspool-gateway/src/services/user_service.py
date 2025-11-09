"""
User service layer for BotsPool Gateway

This module provides business logic for user operations including registration,
authentication, permission checking, and account management.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4, UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from botspool_shared_utils.auth.password_manager import PasswordManager
from botspool_shared_utils.auth.rbac import RBACManager
from botspool_shared_utils.auth.jwt_handler import JWTHandler
from botspool_shared_utils.database.queries import UserQueries, SubscriptionQueries
from botspool_shared_utils.database.models import (
    UserModel,
    UserAuthModel,
    UserProfileModel,
    UserPreferencesModel,
    SubscriptionModel,
)
from botspool_shared_utils.models.enums import (
    UserRole,
    SubscriptionTier,
    AuthProvider,
    FrontendType,
    Permission,
    GraphType,
)
from botspool_shared_utils.errors import (
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ErrorCode,
)
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class UserService:
    """
    Service for user operations.

    Handles user registration, authentication, permission checking, and account management.
    """

    def __init__(
        self,
        session: AsyncSession,
        password_manager: PasswordManager,
        jwt_handler: JWTHandler,
        rbac_manager: RBACManager,
        redis_client: Redis,
    ):
        self.session = session
        self.password_manager = password_manager
        self.jwt_handler = jwt_handler
        self.rbac_manager = rbac_manager
        self.redis_client = redis_client

        self.user_queries = UserQueries(session)
        self.subscription_queries = SubscriptionQueries(session)

    async def create_user(
        self,
        email: str,
        username: str,
        password: str,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new user with all relationships.

        Args:
            email: User email
            username: Username
            password: Plain text password
            display_name: Display name (optional)

        Returns:
            Created user data with ID

        Raises:
            ValidationError: If validation fails
        """
        try:
            # Validate email uniqueness
            existing_user = await self.user_queries.get_user_by_email(email)
            if existing_user:
                raise ValidationError(
                    message="Email already registered",
                    field="email",
                    error_code=ErrorCode.VALIDATION_DUPLICATE_VALUE_009,
                )

            # Validate username uniqueness
            existing_user = await self.user_queries.get_user_by_username(username)
            if existing_user:
                raise ValidationError(
                    message="Username already taken",
                    field="username",
                    error_code=ErrorCode.VALIDATION_DUPLICATE_VALUE_009,
                )

            # Validate password strength
            self.password_manager.validate_password_strength(password)

            # Hash password
            password_hash = self.password_manager.hash_password(password)

            # Generate user ID
            user_id = uuid4()

            # Create user auth
            auth = UserAuthModel(
                id=uuid4(),
                user_id=user_id,
                provider=AuthProvider.EMAIL,
                email=email,
                password_hash=password_hash,
                is_verified=False,
                last_login=None,
                failed_login_attempts=0,
                locked_until=None,
            )
            self.session.add(auth)

            # Create user profile
            profile = UserProfileModel(
                id=uuid4(),
                user_id=user_id,
                username=username,
                display_name=display_name or username,
                first_name=None,
                last_name=None,
                avatar_url=None,
                bio=None,
                timezone="UTC",
                language="en",
                country=None,
            )
            self.session.add(profile)

            # Create user preferences
            preferences = UserPreferencesModel(
                id=uuid4(),
                user_id=user_id,
                email_notifications=True,
                push_notifications=True,
                sms_notifications=False,
                default_graph=None,
                auto_route=True,
                chat_history_retention=30,
                data_sharing=False,
                profile_visibility="private",
                theme="light",
                compact_mode=False,
                debug_mode=False,
                beta_features=False,
            )
            self.session.add(preferences)

            # Create main user record
            user = UserModel(
                id=user_id,
                role=UserRole.FREE_USER,
                subscription_tier=SubscriptionTier.FREE,
                is_active=True,
                is_suspended=False,
                email_verified_at=None,
                last_activity=None,
                total_chats=0,
                total_messages=0,
            )
            self.session.add(user)

            # Create subscription record
            # Get FREE subscription plan
            plan = await self.subscription_queries.get_subscription_plan_by_tier(
                SubscriptionTier.FREE
            )
            if plan:
                # For FREE tier, set next_billing_date far in the future (effectively permanent)
                subscription = SubscriptionModel(
                    id=uuid4(),
                    user_id=user_id,
                    plan_id=plan.id,
                    status="active",
                    billing_cycle=plan.billing_cycle,
                    next_billing_date=datetime.utcnow()
                    + timedelta(days=365 * 10),  # 10 years for FREE
                    last_billing_date=None,
                    is_trial=False,
                    trial_ends_at=None,
                    payment_method_id=None,
                    stripe_subscription_id=None,
                    cancelled_at=None,
                    cancellation_reason=None,
                    is_active=True,
                )
                self.session.add(subscription)

            # Commit all changes
            await self.session.commit()

            logger.info(f"User {user_id} registered successfully with email {email}")

            return {
                "id": user_id,
                "email": email,
                "username": username,
                "display_name": display_name or username,
                "role": UserRole.FREE_USER,
                "subscription_tier": SubscriptionTier.FREE,
            }

        except Exception as exc:
            await self.session.rollback()
            logger.error(f"User creation failed: {exc}")
            raise

    async def authenticate_user(
        self, username_or_email: str, password: str, frontend_type: FrontendType
    ) -> Dict[str, Any]:
        """
        Authenticate user with credentials.

        Args:
            username_or_email: Username or email
            password: Plain text password
            frontend_type: Frontend type

        Returns:
            Authentication result with tokens and user info

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Get user by email or username
            user = None
            if "@" in username_or_email:
                user = await self.user_queries.get_user_by_email(username_or_email)
            else:
                user = await self.user_queries.get_user_by_username(username_or_email)

            if not user or not user.auth:
                raise AuthenticationError(
                    message="Invalid credentials",
                    error_code=ErrorCode.AUTH_PASSWORD_INCORRECT_006,
                )

            # Check if account is locked
            if user.auth.locked_until and user.auth.locked_until > datetime.utcnow():
                remaining_minutes = (
                    user.auth.locked_until - datetime.utcnow()
                ).total_seconds() / 60
                raise AuthenticationError(
                    message=f"Account locked. Try again in {int(remaining_minutes)} minutes",
                    error_code=ErrorCode.AUTH_ACCOUNT_LOCKED_005,
                )

            # Check if account is active
            if not user.is_active:
                raise AuthenticationError(
                    message="Account is inactive",
                    error_code=ErrorCode.AUTH_ACCOUNT_INACTIVE_006,
                )

            # Check if account is suspended
            if user.is_suspended:
                raise AuthenticationError(
                    message="Account is suspended",
                    error_code=ErrorCode.AUTH_ACCOUNT_SUSPENDED_007,
                )

            # Verify password
            if not self.password_manager.verify_password(
                password, user.auth.password_hash
            ):
                await self.handle_failed_login(user.id)
                raise AuthenticationError(
                    message="Invalid credentials",
                    error_code=ErrorCode.AUTH_PASSWORD_INCORRECT_006,
                )

            # Reset failed login attempts on success
            await self.session.execute(
                update(UserAuthModel)
                .where(UserAuthModel.user_id == user.id)
                .values(
                    failed_login_attempts=0,
                    locked_until=None,
                    last_login=datetime.utcnow(),
                )
            )

            # Get user permissions and allowed graphs
            permissions = self.rbac_manager.get_user_permissions(user.role)
            allowed_graphs = self.rbac_manager.get_user_allowed_graphs(user.role)

            # Generate JWT tokens (jti is automatically included by JWT handler)
            access_token = self.jwt_handler.generate_access_token(
                user_id=str(user.id),
                role=user.role,
                permissions=list(permissions),
                frontend_type=frontend_type,
                allowed_graphs=allowed_graphs,
            )

            refresh_token = self.jwt_handler.generate_refresh_token(str(user.id))

            await self.session.commit()

            logger.info(
                f"User {user.id} authenticated successfully via {frontend_type.value}"
            )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.jwt_handler.access_token_expiry,
                "user": {
                    "id": user.id,
                    "email": user.auth.email,
                    "username": user.profile.username,
                    "display_name": user.profile.display_name,
                    "role": user.role,
                    "subscription_tier": user.subscription_tier,
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "last_activity": user.last_activity,
                    "permissions": [p.value for p in permissions],
                },
            }

        except AuthenticationError:
            await self.session.rollback()
            raise
        except Exception as exc:
            await self.session.rollback()
            logger.error(f"Authentication failed: {exc}")
            raise AuthenticationError(
                message="Authentication failed",
                error_code=ErrorCode.AUTH_LOGIN_FAILED_004,
            )

    async def handle_failed_login(self, user_id: UUID) -> None:
        """
        Handle failed login attempt.

        Locks account after 5 failed attempts for 30 minutes.

        Args:
            user_id: User ID
        """
        user = await self.user_queries.get_user_by_id(user_id)
        if not user or not user.auth:
            return

        failed_attempts = user.auth.failed_login_attempts + 1

        # Lock account after 5 failed attempts
        locked_until = None
        if failed_attempts >= 5:
            locked_until = datetime.utcnow() + timedelta(minutes=30)
            logger.warning(
                f"User {user_id} account locked due to {failed_attempts} failed login attempts"
            )

        await self.session.execute(
            update(UserAuthModel)
            .where(UserAuthModel.user_id == user_id)
            .values(failed_login_attempts=failed_attempts, locked_until=locked_until)
        )
        await self.session.commit()

    async def get_user_by_id(self, user_id: UUID) -> Optional[UserModel]:
        """
        Get user by ID with all relationships.

        Args:
            user_id: User ID

        Returns:
            UserModel or None
        """
        return await self.user_queries.get_user_by_id(user_id)

    async def get_user_subscription(self, user_id: UUID) -> Optional[SubscriptionModel]:
        """
        Get user's active subscription.

        Args:
            user_id: User ID

        Returns:
            SubscriptionModel or None
        """
        return await self.subscription_queries.get_subscription_by_user_id(user_id)

    async def check_user_permissions(
        self, user_id: str, graph_type: GraphType
    ) -> Dict[str, Any]:
        """
        Check if user has permission to access graph and get subscription limits.

        Args:
            user_id: User ID
            graph_type: Graph type

        Returns:
            Dict with permission status and limits

        Raises:
            AuthorizationError: If user lacks permission
        """
        try:
            user_uuid = UUID(user_id)
            user = await self.user_queries.get_user_by_id(user_uuid)

            if not user:
                raise AuthorizationError(
                    message="User not found",
                    error_code=ErrorCode.AUTH_USER_NOT_FOUND_004,
                    details={"user_id": user_id},
                )

            # Check if account is active
            if not user.is_active:
                raise AuthorizationError(
                    message="Account is inactive",
                    error_code=ErrorCode.AUTH_ACCOUNT_INACTIVE_006,
                    details={"user_id": user_id},
                )

            # Check if account is suspended
            if user.is_suspended:
                raise AuthorizationError(
                    message="Account is suspended",
                    error_code=ErrorCode.AUTH_ACCOUNT_SUSPENDED_007,
                    details={"user_id": user_id},
                )

            # Get subscription
            subscription = await self.get_user_subscription(user_uuid)

            # Check if user has access to this graph type
            allowed_graphs = self.rbac_manager.get_user_allowed_graphs(user.role)

            if graph_type not in allowed_graphs:
                raise AuthorizationError(
                    message=f"Access denied to {graph_type.value} graph",
                    error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS_003,
                    details={
                        "user_id": user_id,
                        "graph_type": graph_type.value,
                        "user_role": user.role.value,
                    },
                )

            # Get subscription limits if available
            limits = None
            if subscription and subscription.plan:
                limits = {
                    "requests_per_minute": subscription.plan.limits.get(
                        "requests_per_minute", 60
                    ),
                    "requests_per_hour": subscription.plan.limits.get(
                        "requests_per_hour", 1000
                    ),
                    "requests_per_day": subscription.plan.limits.get(
                        "requests_per_day", 10000
                    ),
                }

            return {
                "user_id": str(user.id),
                "role": user.role,
                "subscription_tier": user.subscription_tier,
                "graph_access": True,
                "limits": limits,
            }

        except AuthorizationError:
            raise
        except Exception as exc:
            logger.error(f"Permission check failed: {exc}")
            raise AuthorizationError(
                message="Permission check failed",
                error_code=ErrorCode.AUTHZ_ACCESS_DENIED_001,
            )
