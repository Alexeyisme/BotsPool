"""
Role-Based Access Control (RBAC) for BotsPool

This module provides RBAC functionality including role definitions,
permission checking, and access control.
"""

from enum import Enum
from typing import Dict, List, Set, Optional
from uuid import UUID

from ..models.enums import UserRole, Permission, GraphType
from ..errors import InsufficientPermissionsError


class Role:
    """Role definition with permissions and access."""

    def __init__(
        self,
        name: str,
        permissions: Set[Permission],
        graph_access: Set[GraphType],
        rate_limits: Dict[str, int],
    ):
        self.name = name
        self.permissions = permissions
        self.graph_access = graph_access
        self.rate_limits = rate_limits

    def has_permission(self, permission: Permission) -> bool:
        """Check if role has specific permission."""
        return permission in self.permissions

    def can_access_graph(self, graph_type: GraphType) -> bool:
        """Check if role can access specific graph."""
        return graph_type in self.graph_access

    def get_rate_limit(self, limit_type: str) -> int:
        """Get rate limit for specific type."""
        return self.rate_limits.get(limit_type, 0)


class RBACManager:
    """
    Role-Based Access Control manager for BotsPool.

    Manages roles, permissions, and access control for the platform.
    """

    def __init__(self):
        self.roles = self._initialize_roles()
        self.permission_hierarchy = self._initialize_permission_hierarchy()

    def _initialize_roles(self) -> Dict[UserRole, Role]:
        """Initialize system roles with permissions and access."""
        return {
            UserRole.FREE_USER: Role(
                name="Free User",
                permissions={
                    Permission.READ_GRAPHS,
                },
                graph_access={GraphType.TODO},
                rate_limits={
                    "requests_per_minute": 10,
                    "requests_per_hour": 100,
                    "requests_per_day": 500,
                    "tokens_per_day": 10000,
                },
            ),
            UserRole.BASIC_USER: Role(
                name="Basic User",
                permissions={
                    Permission.READ_GRAPHS,
                    Permission.WRITE_GRAPHS,
                },
                graph_access={GraphType.TODO, GraphType.EMAIL},
                rate_limits={
                    "requests_per_minute": 30,
                    "requests_per_hour": 500,
                    "requests_per_day": 2000,
                    "tokens_per_day": 50000,
                },
            ),
            UserRole.PREMIUM_USER: Role(
                name="Premium User",
                permissions={
                    Permission.READ_GRAPHS,
                    Permission.WRITE_GRAPHS,
                    Permission.VIEW_ANALYTICS,
                },
                graph_access={
                    GraphType.TODO,
                    GraphType.EMAIL,
                    GraphType.CALENDAR,
                    GraphType.DOCUMENT,
                },
                rate_limits={
                    "requests_per_minute": 60,
                    "requests_per_hour": 1000,
                    "requests_per_day": 5000,
                    "tokens_per_day": 100000,
                },
            ),
            UserRole.ENTERPRISE_USER: Role(
                name="Enterprise User",
                permissions={
                    Permission.READ_GRAPHS,
                    Permission.WRITE_GRAPHS,
                    Permission.VIEW_ANALYTICS,
                    Permission.MANAGE_USERS,
                },
                graph_access={
                    GraphType.TODO,
                    GraphType.EMAIL,
                    GraphType.CALENDAR,
                    GraphType.DOCUMENT,
                    GraphType.CODE,
                    GraphType.RESEARCH,
                },
                rate_limits={
                    "requests_per_minute": 200,
                    "requests_per_hour": 5000,
                    "requests_per_day": 20000,
                    "tokens_per_day": 500000,
                },
            ),
            UserRole.ADMIN: Role(
                name="Administrator",
                permissions=set(Permission),  # All permissions
                graph_access=set(GraphType),  # All graphs
                rate_limits={
                    "requests_per_minute": 1000,
                    "requests_per_hour": 10000,
                    "requests_per_day": 100000,
                    "tokens_per_day": 1000000,
                },
            ),
            UserRole.DEVELOPER: Role(
                name="Developer",
                permissions={
                    Permission.READ_GRAPHS,
                    Permission.WRITE_GRAPHS,
                    Permission.ADMIN_GRAPHS,
                },
                graph_access=set(GraphType),  # All graphs
                rate_limits={
                    "requests_per_minute": 100,
                    "requests_per_hour": 2000,
                    "requests_per_day": 10000,
                    "tokens_per_day": 200000,
                },
            ),
        }

    def _initialize_permission_hierarchy(self) -> Dict[Permission, Set[Permission]]:
        """Initialize permission hierarchy for inheritance."""
        return {
            Permission.SYSTEM_ADMIN: set(Permission),
            Permission.MANAGE_INFRASTRUCTURE: {
                Permission.MANAGE_USERS,
                Permission.VIEW_LOGS,
                Permission.VIEW_ANALYTICS,
            },
            Permission.ADMIN_GRAPHS: {Permission.READ_GRAPHS, Permission.WRITE_GRAPHS},
            Permission.MANAGE_USERS: {Permission.VIEW_ANALYTICS},
        }

    def get_role(self, user_role: UserRole) -> Optional[Role]:
        """Get role definition by user role."""
        return self.roles.get(user_role)

    def check_permission(self, user_role: UserRole, permission: Permission) -> bool:
        """
        Check if user role has specific permission.

        Args:
            user_role: User's role
            permission: Permission to check

        Returns:
            True if user has permission, False otherwise
        """
        role = self.get_role(user_role)
        if not role:
            return False

        # Check direct permission
        if role.has_permission(permission):
            return True

        # Check inherited permissions
        for parent_permission, child_permissions in self.permission_hierarchy.items():
            if (
                role.has_permission(parent_permission)
                and permission in child_permissions
            ):
                return True

        return False

    def check_graph_access(self, user_role: UserRole, graph_type: GraphType) -> bool:
        """
        Check if user role can access specific graph.

        Args:
            user_role: User's role
            graph_type: Graph type to check

        Returns:
            True if user can access graph, False otherwise
        """
        role = self.get_role(user_role)
        if not role:
            return False

        return role.can_access_graph(graph_type)

    def get_user_permissions(self, user_role: UserRole) -> Set[Permission]:
        """
        Get all permissions for a user role.

        Args:
            user_role: User's role

        Returns:
            Set of permissions
        """
        role = self.get_role(user_role)
        if not role:
            return set()

        permissions = role.permissions.copy()

        # Add inherited permissions
        for parent_permission, child_permissions in self.permission_hierarchy.items():
            if role.has_permission(parent_permission):
                permissions.update(child_permissions)

        return permissions

    def get_user_graph_access(self, user_role: UserRole) -> Set[GraphType]:
        """
        Get all graph types a user role can access.

        Args:
            user_role: User's role

        Returns:
            Set of accessible graph types
        """
        role = self.get_role(user_role)
        if not role:
            return set()

        return role.graph_access.copy()

    def get_user_allowed_graphs(self, user_role: UserRole) -> List[GraphType]:
        """
        Get all graph types a user role can access as a list.

        Args:
            user_role: User's role

        Returns:
            List of accessible graph types
        """
        graph_access = self.get_user_graph_access(user_role)
        return list(graph_access)

    def get_rate_limits(self, user_role: UserRole) -> Dict[str, int]:
        """
        Get rate limits for a user role.

        Args:
            user_role: User's role

        Returns:
            Dictionary of rate limits
        """
        role = self.get_role(user_role)
        if not role:
            return {}

        return role.rate_limits.copy()

    def require_permission(self, user_role: UserRole, permission: Permission) -> None:
        """
        Require specific permission for user role.

        Args:
            user_role: User's role
            permission: Required permission

        Raises:
            InsufficientPermissionsError: If user doesn't have permission
        """
        if not self.check_permission(user_role, permission):
            raise InsufficientPermissionsError(
                required_permission=permission.value, user_role=user_role.value
            )

    def require_graph_access(self, user_role: UserRole, graph_type: GraphType) -> None:
        """
        Require graph access for user role.

        Args:
            user_role: User's role
            graph_type: Required graph type

        Raises:
            InsufficientPermissionsError: If user doesn't have graph access
        """
        if not self.check_graph_access(user_role, graph_type):
            raise InsufficientPermissionsError(
                required_permission=f"access_{graph_type.value}_graph",
                user_role=user_role.value,
            )

    def can_user_access_feature(self, user_role: UserRole, feature: str) -> bool:
        """
        Check if user can access a specific feature.

        Args:
            user_role: User's role
            feature: Feature name

        Returns:
            True if user can access feature, False otherwise
        """
        # Map features to permissions
        feature_permissions = {
            "analytics": Permission.VIEW_ANALYTICS,
            "user_management": Permission.MANAGE_USERS,
            "system_admin": Permission.SYSTEM_ADMIN,
            "graph_admin": Permission.ADMIN_GRAPHS,
            "infrastructure": Permission.MANAGE_INFRASTRUCTURE,
            "logs": Permission.VIEW_LOGS,
        }

        required_permission = feature_permissions.get(feature)
        if not required_permission:
            return False

        return self.check_permission(user_role, required_permission)

    def get_role_hierarchy(self) -> Dict[str, List[str]]:
        """
        Get role hierarchy for display purposes.

        Returns:
            Dictionary mapping roles to their sub-roles
        """
        return {
            "admin": [
                "developer",
                "enterprise_user",
                "premium_user",
                "basic_user",
                "free_user",
            ],
            "developer": ["enterprise_user", "premium_user", "basic_user", "free_user"],
            "enterprise_user": ["premium_user", "basic_user", "free_user"],
            "premium_user": ["basic_user", "free_user"],
            "basic_user": ["free_user"],
            "free_user": [],
        }


# Global RBAC manager instance
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Get the global RBAC manager instance."""
    global _rbac_manager

    if _rbac_manager is None:
        _rbac_manager = RBACManager()

    return _rbac_manager


def check_permission(user_role: UserRole, permission: Permission) -> bool:
    """Check if user role has specific permission."""
    manager = get_rbac_manager()
    return manager.check_permission(user_role, permission)


def check_graph_access(user_role: UserRole, graph_type: GraphType) -> bool:
    """Check if user role can access specific graph."""
    manager = get_rbac_manager()
    return manager.check_graph_access(user_role, graph_type)


def get_user_permissions(user_role: UserRole) -> Set[Permission]:
    """Get all permissions for a user role."""
    manager = get_rbac_manager()
    return manager.get_user_permissions(user_role)


def get_user_allowed_graphs(user_role: UserRole) -> List[GraphType]:
    """Get all graph types a user role can access."""
    manager = get_rbac_manager()
    return manager.get_user_allowed_graphs(user_role)
