"""
Authentication service for BotsPool

This module provides the main authentication service that coordinates
all authentication components including JWT, sessions, MFA, and OAuth.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from ..errors import (
    AuthenticationError,
    InvalidTokenError,
    TokenExpiredError,
    InsufficientPermissionsError,
)
from ..models.enums import UserRole, Permission, GraphType, FrontendType, AuthProvider
from .jwt_handler import JWTHandler, get_jwt_handler
from .password_manager import PasswordManager, get_password_manager
from .rbac import RBACManager, get_rbac_manager
from .session_manager import SessionManager, get_session_manager
from .mfa import MFAHandler, get_mfa_handler
from .oauth import OAuthManager, get_oauth_manager


class AuthService:
    """
    Main authentication service for BotsPool.

    Coordinates all authentication components and provides
    a unified interface for authentication operations.
    """

    def __init__(
        self,
        jwt_handler: Optional[JWTHandler] = None,
        password_manager: Optional[PasswordManager] = None,
        rbac_manager: Optional[RBACManager] = None,
        session_manager: Optional[SessionManager] = None,
        mfa_handler: Optional[MFAHandler] = None,
        oauth_manager: Optional[OAuthManager] = None,
    ):
        self.jwt_handler = jwt_handler or get_jwt_handler()
        self.password_manager = password_manager or get_password_manager()
        self.rbac_manager = rbac_manager or get_rbac_manager()
        self.session_manager = session_manager
        self.mfa_handler = mfa_handler or get_mfa_handler()
        self.oauth_manager = oauth_manager or get_oauth_manager()
        self.logger = logging.getLogger(__name__)

    async def authenticate_user(
        self,
        email: str,
        password: str,
        frontend_type: FrontendType,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: User password
            frontend_type: Frontend type
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Authentication result with tokens and user info
        """
        try:
            # This would typically query the database to get user
            # For now, we'll simulate the authentication
            user = await self._get_user_by_email(email)
            if not user:
                raise AuthenticationError("Invalid email or password")

            # Verify password
            if not self.password_manager.verify_password(
                password, user["password_hash"]
            ):
                raise AuthenticationError("Invalid email or password")

            # Check if user is active
            if not user.get("is_active", True):
                raise AuthenticationError("User account is inactive")

            # Check if user is suspended
            if user.get("is_suspended", False):
                raise AuthenticationError("User account is suspended")

            # Check MFA requirement
            if user.get("mfa_enabled", False):
                # MFA is required - return partial authentication
                return {
                    "requires_mfa": True,
                    "user_id": user["id"],
                    "message": "MFA verification required",
                }

            # Generate tokens
            user_role = UserRole(user.get("role", UserRole.FREE_USER.value))
            permissions = self.rbac_manager.get_user_permissions(user_role)
            allowed_graphs = self.rbac_manager.get_user_allowed_graphs(user_role)

            access_token = self.jwt_handler.generate_access_token(
                user_id=user["id"],
                role=user_role,
                permissions=permissions,
                frontend_type=frontend_type,
                allowed_graphs=allowed_graphs,
            )

            refresh_token = self.jwt_handler.generate_refresh_token(user["id"])

            # Create session if session manager is available
            session_id = str(uuid4())
            if self.session_manager:
                await self.session_manager.create_session(
                    session_id=session_id,
                    user_id=user["id"],
                    frontend_type=frontend_type,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

            self.logger.info(f"User {user['id']} authenticated successfully")

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.jwt_handler.access_token_expiry,
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                    "role": user_role.value,
                    "permissions": [p.value for p in permissions],
                },
                "session_id": session_id,
            }

        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            raise AuthenticationError(f"Authentication failed: {e}")

    async def verify_mfa(
        self, user_id: Union[str, UUID], mfa_token: str
    ) -> Dict[str, Any]:
        """
        Verify MFA token for user.

        Args:
            user_id: User identifier
            mfa_token: MFA token

        Returns:
            Authentication result with tokens
        """
        try:
            # Get user and MFA secret
            user = await self._get_user_by_id(user_id)
            if not user:
                raise AuthenticationError("User not found")

            mfa_secret = user.get("mfa_secret")
            if not mfa_secret:
                raise AuthenticationError("MFA not enabled for user")

            # Verify MFA token
            if not self.mfa_handler.verify_token(mfa_secret, mfa_token):
                raise AuthenticationError("Invalid MFA token")

            # Generate tokens
            user_role = UserRole(user.get("role", UserRole.FREE_USER.value))
            permissions = self.rbac_manager.get_user_permissions(user_role)

            access_token = self.jwt_handler.generate_access_token(
                user_id=user["id"], role=user_role, permissions=permissions
            )

            refresh_token = self.jwt_handler.generate_refresh_token(user["id"])

            self.logger.info(f"User {user['id']} MFA verified successfully")

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.jwt_handler.access_token_expiry,
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                    "role": user_role.value,
                    "permissions": [p.value for p in permissions],
                },
            }

        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error(f"MFA verification failed: {e}")
            raise AuthenticationError(f"MFA verification failed: {e}")

    async def authenticate_oauth(
        self,
        provider_name: str,
        code: str,
        frontend_type: FrontendType,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate user with OAuth provider.

        Args:
            provider_name: OAuth provider name
            code: Authorization code
            frontend_type: Frontend type
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Authentication result with tokens and user info
        """
        try:
            # Authenticate with OAuth provider
            oauth_user_info = await self.oauth_manager.authenticate_user(
                provider_name, code
            )

            # Find or create user
            user = await self._find_or_create_oauth_user(oauth_user_info)

            # Check if user is active
            if not user.get("is_active", True):
                raise AuthenticationError("User account is inactive")

            # Generate tokens
            user_role = UserRole(user.get("role", UserRole.FREE_USER.value))
            permissions = self.rbac_manager.get_user_permissions(user_role)

            access_token = self.jwt_handler.generate_access_token(
                user_id=user["id"], role=user_role, permissions=permissions
            )

            refresh_token = self.jwt_handler.generate_refresh_token(user["id"])

            # Create session if session manager is available
            session_id = str(uuid4())
            if self.session_manager:
                await self.session_manager.create_session(
                    session_id=session_id,
                    user_id=user["id"],
                    frontend_type=frontend_type,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

            self.logger.info(
                f"User {user['id']} authenticated via OAuth {provider_name}"
            )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.jwt_handler.access_token_expiry,
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                    "role": user_role.value,
                    "permissions": [p.value for p in permissions],
                },
                "session_id": session_id,
            }

        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error(f"OAuth authentication failed: {e}")
            raise AuthenticationError(f"OAuth authentication failed: {e}")

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token and refresh token
        """
        try:
            return self.jwt_handler.refresh_access_token(refresh_token)

        except Exception as e:
            self.logger.error(f"Token refresh failed: {e}")
            raise AuthenticationError(f"Token refresh failed: {e}")

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate access token.

        Args:
            token: Access token to validate

        Returns:
            Token payload if valid
        """
        try:
            return self.jwt_handler.validate_token(token, "access")

        except TokenExpiredError:
            raise
        except InvalidTokenError:
            raise
        except Exception as e:
            self.logger.error(f"Token validation failed: {e}")
            raise InvalidTokenError(f"Token validation failed: {e}")

    async def authorize_user(
        self, user_role: UserRole, required_permission: Permission
    ) -> bool:
        """
        Authorize user for specific permission.

        Args:
            user_role: User's role
            required_permission: Required permission

        Returns:
            True if authorized, False otherwise
        """
        return self.rbac_manager.check_permission(user_role, required_permission)

    async def authorize_graph_access(
        self, user_role: UserRole, graph_type: GraphType
    ) -> bool:
        """
        Authorize user for graph access.

        Args:
            user_role: User's role
            graph_type: Graph type to access

        Returns:
            True if authorized, False otherwise
        """
        return self.rbac_manager.check_graph_access(user_role, graph_type)

    async def require_permission(
        self, user_role: UserRole, required_permission: Permission
    ) -> None:
        """
        Require specific permission for user role.

        Args:
            user_role: User's role
            required_permission: Required permission

        Raises:
            InsufficientPermissionsError: If user doesn't have permission
        """
        self.rbac_manager.require_permission(user_role, required_permission)

    async def require_graph_access(
        self, user_role: UserRole, graph_type: GraphType
    ) -> None:
        """
        Require graph access for user role.

        Args:
            user_role: User's role
            graph_type: Required graph type

        Raises:
            InsufficientPermissionsError: If user doesn't have graph access
        """
        self.rbac_manager.require_graph_access(user_role, graph_type)

    async def create_user_session(
        self, user_id: Union[str, UUID], frontend_type: FrontendType, **kwargs
    ) -> str:
        """
        Create user session.

        Args:
            user_id: User identifier
            frontend_type: Frontend type
            **kwargs: Additional session parameters

        Returns:
            Session ID
        """
        if not self.session_manager:
            raise AuthenticationError("Session manager not available")

        session_id = str(uuid4())
        await self.session_manager.create_session(
            session_id=session_id,
            user_id=user_id,
            frontend_type=frontend_type,
            **kwargs,
        )

        return session_id

    async def revoke_user_session(self, session_id: str) -> bool:
        """
        Revoke user session.

        Args:
            session_id: Session identifier

        Returns:
            True if successful, False otherwise
        """
        if not self.session_manager:
            return False

        return await self.session_manager.delete_session(session_id)

    async def revoke_all_user_sessions(self, user_id: Union[str, UUID]) -> int:
        """
        Revoke all sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of sessions revoked
        """
        if not self.session_manager:
            return 0

        return await self.session_manager.delete_user_sessions(user_id)

    async def _get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email (placeholder implementation)."""
        # This would typically query the database
        # For now, return None to simulate user not found
        return None

    async def _get_user_by_id(
        self, user_id: Union[str, UUID]
    ) -> Optional[Dict[str, Any]]:
        """Get user by ID (placeholder implementation)."""
        # This would typically query the database
        # For now, return None to simulate user not found
        return None

    async def _find_or_create_oauth_user(
        self, oauth_user_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find or create user from OAuth info (placeholder implementation)."""
        # This would typically query the database and create user if not found
        # For now, return a mock user
        return {
            "id": str(uuid4()),
            "email": oauth_user_info["email"],
            "role": UserRole.FREE_USER.value,
            "is_active": True,
            "is_suspended": False,
            "mfa_enabled": False,
        }


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global _auth_service

    if _auth_service is None:
        _auth_service = AuthService()

    return _auth_service


async def authenticate_user(
    email: str, password: str, frontend_type: FrontendType, **kwargs
) -> Dict[str, Any]:
    """Authenticate user with email and password."""
    service = get_auth_service()
    return await service.authenticate_user(email, password, frontend_type, **kwargs)


async def authorize_user(user_role: UserRole, required_permission: Permission) -> bool:
    """Authorize user for specific permission."""
    service = get_auth_service()
    return await service.authorize_user(user_role, required_permission)


async def create_user_session(
    user_id: Union[str, UUID], frontend_type: FrontendType, **kwargs
) -> str:
    """Create user session."""
    service = get_auth_service()
    return await service.create_user_session(user_id, frontend_type, **kwargs)


async def revoke_user_session(session_id: str) -> bool:
    """Revoke user session."""
    service = get_auth_service()
    return await service.revoke_user_session(session_id)
