"""
JWT Authentication dependencies for BotsPool Gateway

This module provides FastAPI dependencies for protecting API endpoints
with JWT-based authentication and RBAC checks.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from botspool_shared_utils.auth.jwt_handler import JWTHandler
from ..dependencies import get_jwt_handler
from botspool_shared_utils.auth.rbac import RBACManager, get_rbac_manager
from botspool_shared_utils.models.enums import (
    UserRole,
    Permission,
    GraphType,
)

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP authorization credentials
        jwt_handler: JWT handler instance

    Returns:
        Dict[str, Any]: User information from token

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Validate token
        payload = jwt_handler.validate_token(credentials.credentials, "access")

        return {
            "user_id": payload.get("sub"),
            "role": payload.get("role"),
            "permissions": payload.get("permissions", []),
            "frontend_type": payload.get("frontend_type"),
            "allowed_graphs": payload.get("allowed_graphs", []),
            "token_payload": payload,
        }

    except Exception as exc:
        logger.warning(f"Token validation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_required(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current user (required authentication).

    Args:
        current_user: Current user from get_current_user

    Returns:
        Dict[str, Any]: User information
    """
    return current_user


async def require_permission(
    permission: Permission,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    rbac_manager: RBACManager = Depends(get_rbac_manager),
) -> Dict[str, Any]:
    """
    Require specific permission for current user.

    Args:
        permission: Required permission
        current_user: Current user information
        rbac_manager: RBAC manager

    Returns:
        Dict[str, Any]: User information

    Raises:
        HTTPException: If user doesn't have permission
    """
    user_role = UserRole(current_user.get("role", "free_user"))

    if not rbac_manager.check_permission(user_role, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {permission.value}",
        )

    return current_user


async def require_graph_access(
    graph_type: GraphType,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    rbac_manager: RBACManager = Depends(get_rbac_manager),
) -> Dict[str, Any]:
    """
    Require access to specific graph type.

    Args:
        graph_type: Required graph type
        current_user: Current user information
        rbac_manager: RBAC manager

    Returns:
        Dict[str, Any]: User information

    Raises:
        HTTPException: If user doesn't have graph access
    """
    user_role = UserRole(current_user.get("role", "free_user"))

    if not rbac_manager.check_graph_access(user_role, graph_type):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to {graph_type.value} graph",
        )

    return current_user


async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """
    Require admin role for current user.

    Args:
        current_user: Current user information

    Returns:
        Dict[str, Any]: User information

    Raises:
        HTTPException: If user is not admin
    """
    user_role = current_user.get("role")

    if user_role not in ["admin", "developer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    return current_user
