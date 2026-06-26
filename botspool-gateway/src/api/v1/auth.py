"""
Authentication API endpoints for BotsPool Gateway

This module provides authentication endpoints including:
- User login
- Token refresh
- User logout
- User registration (future)
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from botspool_shared_utils.auth.jwt_handler import JWTHandler, get_jwt_handler
from botspool_shared_utils.auth.rbac import RBACManager, get_rbac_manager
from botspool_shared_utils.auth.password_manager import PasswordManager
from botspool_shared_utils.models.user import User, UserCreate, UserResponse
from botspool_shared_utils.models.enums import (
    UserRole,
    FrontendType,
    GraphType,
    SubscriptionTier,
)
from botspool_shared_utils.database.connection import DatabaseManager

from ...dependencies import (
    get_database_manager,
    get_redis_client,
    get_db_session,
    get_password_manager,
)
from ...auth.middleware import get_current_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security scheme
security = HTTPBearer(auto_error=False)


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request model."""

    username: str = Field(
        ..., min_length=3, max_length=50, description="Username or email"
    )
    password: str = Field(..., min_length=8, description="Password")
    frontend_type: FrontendType = Field(
        ..., description="Frontend type (telegram, discord, web, etc.)"
    )


class LoginResponse(BaseModel):
    """Login response model."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    refresh_token: str = Field(..., description="JWT refresh token")
    user: UserResponse = Field(..., description="User information")


class RefreshRequest(BaseModel):
    """Token refresh request model."""

    refresh_token: str = Field(..., description="JWT refresh token")
    frontend_type: FrontendType = Field(..., description="Frontend type")


class RefreshResponse(BaseModel):
    """Token refresh response model."""

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    refresh_token: str = Field(..., description="New JWT refresh token")


class LogoutRequest(BaseModel):
    """Logout request model."""

    refresh_token: Optional[str] = Field(None, description="Refresh token to revoke")


class LogoutResponse(BaseModel):
    """Logout response model."""

    message: str = Field(..., description="Logout confirmation message")


class RegisterRequest(BaseModel):
    """User registration request model."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="Password")
    display_name: Optional[str] = Field(
        None, max_length=150, description="Display name"
    )
    frontend_type: FrontendType = Field(..., description="Frontend type")


class RegisterResponse(BaseModel):
    """User registration response model."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    refresh_token: str = Field(..., description="JWT refresh token")
    user: UserResponse = Field(..., description="User information")


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    db_session: AsyncSession = Depends(get_db_session),
    password_manager: PasswordManager = Depends(get_password_manager),
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    rbac_manager: RBACManager = Depends(get_rbac_manager),
    redis_client: Redis = Depends(get_redis_client),
):
    """
    User registration endpoint.

    Creates a new user account and returns JWT tokens.

    Args:
        request: Registration request data
        db_session: Database session
        password_manager: Password manager
        jwt_handler: JWT handler instance
        rbac_manager: RBAC manager instance
        redis_client: Redis client

    Returns:
        RegisterResponse: Authentication tokens and user info

    Raises:
        HTTPException: If registration fails
    """
    from ...services.user_service import UserService

    try:
        # Create user service
        user_service = UserService(
            db_session, password_manager, jwt_handler, rbac_manager, redis_client
        )

        # Create user
        user_data = await user_service.create_user(
            email=request.email,
            username=request.username,
            password=request.password,
            display_name=request.display_name,
        )

        # Authenticate user to get tokens
        auth_result = await user_service.authenticate_user(
            username_or_email=request.username,
            password=request.password,
            frontend_type=request.frontend_type,
        )

        logger.info(
            f"User {user_data['id']} registered successfully via {request.frontend_type.value}"
        )

        return RegisterResponse(
            access_token=auth_result["access_token"],
            expires_in=auth_result["expires_in"],
            refresh_token=auth_result["refresh_token"],
            user=auth_result["user"],
        )

    except Exception as exc:
        logger.error(f"Registration failed unexpectedly: {exc}", exc_info=True)
        raise


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db_session: AsyncSession = Depends(get_db_session),
    password_manager: PasswordManager = Depends(get_password_manager),
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    rbac_manager: RBACManager = Depends(get_rbac_manager),
    redis_client: Redis = Depends(get_redis_client),
):
    """
    User login endpoint.

    Authenticates user credentials and returns JWT tokens.

    Args:
        request: Login request data
        db_session: Database session
        password_manager: Password manager
        jwt_handler: JWT handler instance
        rbac_manager: RBAC manager instance
        redis_client: Redis client

    Returns:
        LoginResponse: Authentication tokens and user info

    Raises:
        HTTPException: If authentication fails
    """
    from ...services.user_service import UserService

    try:
        # Create user service
        user_service = UserService(
            db_session, password_manager, jwt_handler, rbac_manager, redis_client
        )

        # Authenticate user
        auth_result = await user_service.authenticate_user(
            username_or_email=request.username,
            password=request.password,
            frontend_type=request.frontend_type,
        )

        logger.info(
            f"User {auth_result['user']['id']} logged in via {request.frontend_type.value}"
        )

        return LoginResponse(
            access_token=auth_result["access_token"],
            expires_in=auth_result["expires_in"],
            refresh_token=auth_result["refresh_token"],
            user=auth_result["user"],
        )

    except Exception as exc:
        logger.error(
            f"Login failed unexpectedly for user {request.username}: {exc}",
            exc_info=True,
        )
        raise


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request: RefreshRequest,
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    rbac_manager: RBACManager = Depends(get_rbac_manager),
):
    """
    Refresh access token endpoint.

    Generates new access and refresh tokens from a valid refresh token.

    Args:
        request: Refresh request data
        jwt_handler: JWT handler instance
        rbac_manager: RBAC manager instance

    Returns:
        RefreshResponse: New authentication tokens

    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Validate refresh token
        payload = jwt_handler.validate_token(request.refresh_token, "refresh")
        user_id = payload.get("sub")

        # Get user role and permissions (in production, fetch from database)
        user_role = UserRole.BASIC_USER  # Default role
        permissions = rbac_manager.get_user_permissions(user_role)
        allowed_graphs = rbac_manager.get_user_allowed_graphs(user_role)

        # Generate new tokens
        new_access_token = jwt_handler.generate_access_token(
            user_id=user_id,
            role=user_role,
            permissions=list(permissions),
            frontend_type=request.frontend_type,
            allowed_graphs=allowed_graphs,
        )

        new_refresh_token = jwt_handler.generate_refresh_token(user_id)

        logger.info(f"Tokens refreshed for user {user_id}")

        return RefreshResponse(
            access_token=new_access_token,
            expires_in=jwt_handler.access_token_expiry,
            refresh_token=new_refresh_token,
        )

    except Exception as exc:
        logger.warning(f"Token refresh failed: {exc}")
        raise


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: LogoutRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    redis_client=Depends(get_redis_client),
):
    """
    User logout endpoint.

    Revokes user tokens and clears session data.

    Args:
        request: Logout request data
        current_user: Current authenticated user
        jwt_handler: JWT handler instance
        redis_client: Redis client instance

    Returns:
        LogoutResponse: Logout confirmation
    """
    try:
        user_id = current_user.get("user_id")

        # Revoke refresh token if provided
        if request.refresh_token:
            jwt_handler.revoke_token(request.refresh_token)

        # Clear user session data from Redis
        # In production, you might want to:
        # 1. Add tokens to a blacklist
        # 2. Clear user session data
        # 3. Update last logout timestamp

        logger.info(f"User {user_id} logged out")

        return LogoutResponse(message="Successfully logged out")

    except Exception as exc:
        logger.error(f"Logout failed unexpectedly: {exc}", exc_info=True)
        raise


class PasswordResetRequestRequest(BaseModel):
    """Password reset request model."""

    email: EmailStr = Field(..., description="User email address")


class PasswordResetRequestResponse(BaseModel):
    """Password reset request response model."""

    message: str = Field(..., description="Response message")


class PasswordResetVerifyRequest(BaseModel):
    """Password reset token verification request model."""

    token: str = Field(..., description="Password reset token")


class PasswordResetVerifyResponse(BaseModel):
    """Password reset token verification response model."""

    valid: bool = Field(..., description="Token validity")
    message: str = Field(..., description="Response message")


class PasswordResetConfirmRequest(BaseModel):
    """Password reset confirmation request model."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")


class PasswordResetConfirmResponse(BaseModel):
    """Password reset confirmation response model."""

    message: str = Field(..., description="Response message")


@router.post("/password-reset/request", response_model=PasswordResetRequestResponse)
async def request_password_reset(
    request: PasswordResetRequestRequest,
    db_session: AsyncSession = Depends(get_db_session),
    password_manager: PasswordManager = Depends(get_password_manager),
    redis_client: Redis = Depends(get_redis_client),
):
    """
    Request password reset.

    Sends password reset email with reset token.

    Args:
        request: Password reset request data
        db_session: Database session
        password_manager: Password manager
        redis_client: Redis client

    Returns:
        PasswordResetRequestResponse: Success message

    Raises:
        HTTPException: If request fails
    """
    from botspool_shared_utils.database.queries import UserQueries

    try:
        user_queries = UserQueries(db_session)
        user = await user_queries.get_user_by_email(request.email)

        # Always return success (don't reveal if email exists)
        if user:
            # Generate reset token
            token = password_manager.generate_password_reset_token()

            # Store token in Redis with 1 hour expiry
            redis_key = f"password_reset:{token}"
            await redis_client.setex(redis_key, 3600, str(user.id))  # 1 hour

            # Email delivery requires a transactional email provider (SendGrid,
            # SES, etc.) which is not yet configured. Do NOT deploy to
            # production without replacing this with real email delivery.
            logger.warning(
                "Password reset token generated for user %s - EMAIL DELIVERY "
                "NOT CONFIGURED, token logged for development only: %s...",
                user.id,
                token[:20],
            )

        return PasswordResetRequestResponse(
            message="If the email exists, a password reset link has been sent"
        )

    except Exception as exc:
        logger.error(f"Password reset request failed: {exc}")
        # Still return success to prevent email enumeration
        return PasswordResetRequestResponse(
            message="If the email exists, a password reset link has been sent"
        )


@router.post("/password-reset/verify", response_model=PasswordResetVerifyResponse)
async def verify_password_reset_token(
    request: PasswordResetVerifyRequest, redis_client: Redis = Depends(get_redis_client)
):
    """
    Verify password reset token.

    Checks if password reset token is valid.

    Args:
        request: Token verification request data
        redis_client: Redis client

    Returns:
        PasswordResetVerifyResponse: Token validity
    """
    try:
        redis_key = f"password_reset:{request.token}"
        user_id = await redis_client.get(redis_key)

        if user_id:
            return PasswordResetVerifyResponse(valid=True, message="Token is valid")
        else:
            return PasswordResetVerifyResponse(
                valid=False, message="Token is invalid or expired"
            )

    except Exception as exc:
        logger.error(f"Password reset token verification failed: {exc}")
        return PasswordResetVerifyResponse(
            valid=False, message="Token verification failed"
        )


@router.post("/password-reset/confirm", response_model=PasswordResetConfirmResponse)
async def confirm_password_reset(
    request: PasswordResetConfirmRequest,
    db_session: AsyncSession = Depends(get_db_session),
    password_manager: PasswordManager = Depends(get_password_manager),
    redis_client: Redis = Depends(get_redis_client),
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
):
    """
    Confirm password reset and set new password.

    Validates token and updates user password, invalidating all existing sessions.

    Args:
        request: Password reset confirmation data
        db_session: Database session
        password_manager: Password manager
        redis_client: Redis client
        jwt_handler: JWT handler instance

    Returns:
        PasswordResetConfirmResponse: Success message

    Raises:
        HTTPException: If confirmation fails
    """
    from botspool_shared_utils.database.queries import UserQueries
    from sqlalchemy import update
    from botspool_shared_utils.database.models import UserAuthModel

    try:
        # Verify token
        redis_key = f"password_reset:{request.token}"
        user_id = await redis_client.get(redis_key)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Validate password strength
        password_manager.validate_password_strength(request.new_password)

        # Hash new password
        password_hash = password_manager.hash_password(request.new_password)

        # Update password in database
        user_queries = UserQueries(db_session)
        await db_session.execute(
            update(UserAuthModel)
            .where(UserAuthModel.user_id == user_id)
            .values(password_hash=password_hash)
        )
        await db_session.commit()

        # Delete reset token from Redis
        await redis_client.delete(redis_key)

        # Invalidate all tokens issued before this point
        user_id_str = user_id.decode() if isinstance(user_id, bytes) else str(user_id)
        await jwt_handler.revoke_all_user_tokens(user_id_str)

        logger.info(f"Password reset completed for user {user_id}")

        return PasswordResetConfirmResponse(
            message="Password has been reset successfully"
        )

    except HTTPException:
        raise
    except Exception as exc:
        await db_session.rollback()
        logger.error(f"Password reset confirmation failed: {exc}", exc_info=True)
        raise


@router.get("/me")
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current user information.

    Returns information about the currently authenticated user.

    Args:
        current_user: Current authenticated user

    Returns:
        Dict[str, Any]: User information
    """
    return {
        "user_id": current_user.get("user_id"),
        "role": current_user.get("role"),
        "permissions": current_user.get("permissions"),
        "frontend_type": current_user.get("frontend_type"),
        "allowed_graphs": current_user.get("allowed_graphs"),
    }


@router.get("/permissions")
async def get_user_permissions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager),
):
    """
    Get user permissions.

    Returns detailed permission information for the current user.

    Args:
        current_user: Current authenticated user
        rbac_manager: RBAC manager instance

    Returns:
        Dict[str, Any]: Permission information
    """
    user_role = UserRole(current_user.get("role", "free_user"))

    return {
        "role": user_role.value,
        "permissions": [p.value for p in rbac_manager.get_user_permissions(user_role)],
        "allowed_graphs": [
            g.value for g in rbac_manager.get_user_allowed_graphs(user_role)
        ],
        "rate_limits": rbac_manager.get_rate_limits(user_role),
    }
