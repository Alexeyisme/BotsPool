"""
Unit tests for enum definitions
"""

import pytest
from botspool_shared_utils.models.enums import (
    SubscriptionTier,
    GraphType,
    UserRole,
    Permission,
    ChatStatus,
    GraphStatus,
    FrontendType,
    AuthProvider,
    TokenType,
    ErrorSeverity,
    ErrorCategory,
    HealthStatus,
    CircuitState,
    CacheStrategy,
    LogLevel,
)


class TestSubscriptionTier:
    """Test SubscriptionTier enum."""

    def test_subscription_tier_values(self):
        """Test that SubscriptionTier has correct values."""
        assert SubscriptionTier.FREE == "free"
        assert SubscriptionTier.BASIC == "basic"
        assert SubscriptionTier.PREMIUM == "premium"
        assert SubscriptionTier.ENTERPRISE == "enterprise"

    def test_subscription_tier_string_conversion(self):
        """Test that SubscriptionTier converts to string correctly."""
        assert SubscriptionTier.FREE.value == "free"
        assert SubscriptionTier.PREMIUM.value == "premium"

    def test_subscription_tier_comparison(self):
        """Test that SubscriptionTier can be compared."""
        assert SubscriptionTier.FREE == "free"
        assert SubscriptionTier.BASIC != "free"
        assert SubscriptionTier.PREMIUM > SubscriptionTier.BASIC


class TestGraphType:
    """Test GraphType enum."""

    def test_graph_type_values(self):
        """Test that GraphType has correct values."""
        assert GraphType.TODO == "todo"
        assert GraphType.EMAIL == "email"
        assert GraphType.CALENDAR == "calendar"
        assert GraphType.DOCUMENT == "document"
        assert GraphType.CODE == "code"
        assert GraphType.RESEARCH == "research"

    def test_graph_type_string_conversion(self):
        """Test that GraphType converts to string correctly."""
        assert GraphType.TODO.value == "todo"
        assert GraphType.EMAIL.value == "email"


class TestUserRole:
    """Test UserRole enum."""

    def test_user_role_values(self):
        """Test that UserRole has correct values."""
        assert UserRole.FREE_USER == "free_user"
        assert UserRole.BASIC_USER == "basic_user"
        assert UserRole.PREMIUM_USER == "premium_user"
        assert UserRole.ENTERPRISE_USER == "enterprise_user"
        assert UserRole.ADMIN == "admin"
        assert UserRole.DEVELOPER == "developer"

    def test_user_role_hierarchy(self):
        """Test that UserRole hierarchy makes sense."""
        # Admin should have highest privileges
        assert UserRole.ADMIN != UserRole.FREE_USER
        assert UserRole.DEVELOPER != UserRole.FREE_USER


class TestPermission:
    """Test Permission enum."""

    def test_permission_values(self):
        """Test that Permission has correct values."""
        assert Permission.READ_GRAPHS == "read_graphs"
        assert Permission.WRITE_GRAPHS == "write_graphs"
        assert Permission.ADMIN_GRAPHS == "admin_graphs"
        assert Permission.MANAGE_USERS == "manage_users"
        assert Permission.VIEW_ANALYTICS == "view_analytics"
        assert Permission.MANAGE_SUBSCRIPTIONS == "manage_subscriptions"
        assert Permission.SYSTEM_ADMIN == "system_admin"
        assert Permission.VIEW_LOGS == "view_logs"
        assert Permission.MANAGE_INFRASTRUCTURE == "manage_infrastructure"

    def test_permission_string_conversion(self):
        """Test that Permission converts to string correctly."""
        assert Permission.READ_GRAPHS.value == "read_graphs"
        assert Permission.ADMIN_GRAPHS.value == "admin_graphs"


class TestChatStatus:
    """Test ChatStatus enum."""

    def test_chat_status_values(self):
        """Test that ChatStatus has correct values."""
        assert ChatStatus.ACTIVE == "active"
        assert ChatStatus.PAUSED == "paused"
        assert ChatStatus.ENDED == "ended"
        assert ChatStatus.ERROR == "error"

    def test_chat_status_string_conversion(self):
        """Test that ChatStatus converts to string correctly."""
        assert ChatStatus.ACTIVE.value == "active"
        assert ChatStatus.ERROR.value == "error"


class TestGraphStatus:
    """Test GraphStatus enum."""

    def test_graph_status_values(self):
        """Test that GraphStatus has correct values."""
        assert GraphStatus.HEALTHY == "healthy"
        assert GraphStatus.DEGRADED == "degraded"
        assert GraphStatus.UNHEALTHY == "unhealthy"
        assert GraphStatus.MAINTENANCE == "maintenance"
        assert GraphStatus.OFFLINE == "offline"

    def test_graph_status_string_conversion(self):
        """Test that GraphStatus converts to string correctly."""
        assert GraphStatus.HEALTHY.value == "healthy"
        assert GraphStatus.OFFLINE.value == "offline"


class TestFrontendType:
    """Test FrontendType enum."""

    def test_frontend_type_values(self):
        """Test that FrontendType has correct values."""
        assert FrontendType.TELEGRAM == "telegram"
        assert FrontendType.DISCORD == "discord"
        assert FrontendType.WEB == "web"
        assert FrontendType.MOBILE == "mobile"
        assert FrontendType.API == "api"

    def test_frontend_type_string_conversion(self):
        """Test that FrontendType converts to string correctly."""
        assert FrontendType.TELEGRAM.value == "telegram"
        assert FrontendType.WEB.value == "web"


class TestAuthProvider:
    """Test AuthProvider enum."""

    def test_auth_provider_values(self):
        """Test that AuthProvider has correct values."""
        assert AuthProvider.EMAIL == "email"
        assert AuthProvider.GOOGLE == "google"
        assert AuthProvider.GITHUB == "github"
        assert AuthProvider.MICROSOFT == "microsoft"

    def test_auth_provider_string_conversion(self):
        """Test that AuthProvider converts to string correctly."""
        assert AuthProvider.EMAIL.value == "email"
        assert AuthProvider.GOOGLE.value == "google"


class TestTokenType:
    """Test TokenType enum."""

    def test_token_type_values(self):
        """Test that TokenType has correct values."""
        assert TokenType.ACCESS == "access"
        assert TokenType.REFRESH == "refresh"
        assert TokenType.MFA == "mfa"
        assert TokenType.PASSWORD_RESET == "password_reset"

    def test_token_type_string_conversion(self):
        """Test that TokenType converts to string correctly."""
        assert TokenType.ACCESS.value == "access"
        assert TokenType.REFRESH.value == "refresh"


class TestErrorSeverity:
    """Test ErrorSeverity enum."""

    def test_error_severity_values(self):
        """Test that ErrorSeverity has correct values."""
        assert ErrorSeverity.LOW == "low"
        assert ErrorSeverity.MEDIUM == "medium"
        assert ErrorSeverity.HIGH == "high"
        assert ErrorSeverity.CRITICAL == "critical"

    def test_error_severity_hierarchy(self):
        """Test that ErrorSeverity hierarchy makes sense."""
        # Critical should be highest severity
        assert ErrorSeverity.CRITICAL != ErrorSeverity.LOW
        assert ErrorSeverity.HIGH != ErrorSeverity.LOW


class TestErrorCategory:
    """Test ErrorCategory enum."""

    def test_error_category_values(self):
        """Test that ErrorCategory has correct values."""
        assert ErrorCategory.AUTHENTICATION == "authentication"
        assert ErrorCategory.AUTHORIZATION == "authorization"
        assert ErrorCategory.VALIDATION == "validation"
        assert ErrorCategory.GRAPH_SERVICE == "graph_service"
        assert ErrorCategory.DATABASE == "database"
        assert ErrorCategory.EXTERNAL_SERVICE == "external_service"
        assert ErrorCategory.RATE_LIMIT == "rate_limit"
        assert ErrorCategory.SERVER == "server"
        assert ErrorCategory.UNKNOWN == "unknown"
        assert ErrorCategory.CONFIGURATION == "configuration"

    def test_error_category_string_conversion(self):
        """Test that ErrorCategory converts to string correctly."""
        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.DATABASE.value == "database"


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_health_status_values(self):
        """Test that HealthStatus has correct values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"
        assert HealthStatus.UNKNOWN == "unknown"

    def test_health_status_string_conversion(self):
        """Test that HealthStatus converts to string correctly."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestCircuitState:
    """Test CircuitState enum."""

    def test_circuit_state_values(self):
        """Test that CircuitState has correct values."""
        assert CircuitState.CLOSED == "closed"
        assert CircuitState.OPEN == "open"
        assert CircuitState.HALF_OPEN == "half_open"

    def test_circuit_state_string_conversion(self):
        """Test that CircuitState converts to string correctly."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"


class TestCacheStrategy:
    """Test CacheStrategy enum."""

    def test_cache_strategy_values(self):
        """Test that CacheStrategy has correct values."""
        assert CacheStrategy.NO_CACHE == "no_cache"
        assert CacheStrategy.READ_THROUGH == "read_through"
        assert CacheStrategy.WRITE_THROUGH == "write_through"
        assert CacheStrategy.WRITE_BACK == "write_back"
        assert CacheStrategy.CACHE_ASIDE == "cache_aside"

    def test_cache_strategy_string_conversion(self):
        """Test that CacheStrategy converts to string correctly."""
        assert CacheStrategy.NO_CACHE.value == "no_cache"
        assert CacheStrategy.READ_THROUGH.value == "read_through"


class TestLogLevel:
    """Test LogLevel enum."""

    def test_log_level_values(self):
        """Test that LogLevel has correct values."""
        assert LogLevel.DEBUG == "debug"
        assert LogLevel.INFO == "info"
        assert LogLevel.WARNING == "warning"
        assert LogLevel.ERROR == "error"
        assert LogLevel.CRITICAL == "critical"

    def test_log_level_hierarchy(self):
        """Test that LogLevel hierarchy makes sense."""
        # Critical should be highest level
        assert LogLevel.CRITICAL != LogLevel.DEBUG
        assert LogLevel.ERROR != LogLevel.DEBUG
