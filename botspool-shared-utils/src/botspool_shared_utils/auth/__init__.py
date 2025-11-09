"""
BotsPool Authentication Utilities

This module provides authentication and authorization utilities for the BotsPool platform,
including JWT management, RBAC, password security, and session management.
"""

from .jwt_handler import (
    JWTHandler,
    create_jwt_handler,
    generate_token,
    validate_token,
    refresh_token,
)

from .password_manager import (
    PasswordManager,
    hash_password,
    verify_password,
    generate_password_reset_token,
    verify_password_reset_token,
)

from .rbac import (
    RBACManager,
    Permission,
    Role,
    check_permission,
    check_graph_access,
    get_user_permissions,
)

from .session_manager import (
    SessionManager,
    create_session,
    get_session,
    update_session,
    delete_session,
    cleanup_expired_sessions,
)

from .mfa import (
    MFAHandler,
    generate_mfa_secret,
    generate_mfa_qr_code,
    verify_mfa_token,
    is_mfa_enabled,
)

from .oauth import OAuthProvider, GoogleOAuthProvider, GitHubOAuthProvider, OAuthManager

from .auth_service import (
    AuthService,
    authenticate_user,
    authorize_user,
    create_user_session,
    revoke_user_session,
)

__all__ = [
    # JWT utilities
    "JWTHandler",
    "create_jwt_handler",
    "generate_token",
    "validate_token",
    "refresh_token",
    # Password management
    "PasswordManager",
    "hash_password",
    "verify_password",
    "generate_password_reset_token",
    "verify_password_reset_token",
    # RBAC
    "RBACManager",
    "Permission",
    "Role",
    "check_permission",
    "check_graph_access",
    "get_user_permissions",
    # Session management
    "SessionManager",
    "create_session",
    "get_session",
    "update_session",
    "delete_session",
    "cleanup_expired_sessions",
    # MFA
    "MFAHandler",
    "generate_mfa_secret",
    "generate_mfa_qr_code",
    "verify_mfa_token",
    "is_mfa_enabled",
    # OAuth
    "OAuthProvider",
    "GoogleOAuthProvider",
    "GitHubOAuthProvider",
    "OAuthManager",
    # Auth service
    "AuthService",
    "authenticate_user",
    "authorize_user",
    "create_user_session",
    "revoke_user_session",
]
