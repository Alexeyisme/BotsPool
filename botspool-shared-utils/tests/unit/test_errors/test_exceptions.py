"""
Unit tests for exception hierarchy
"""

import pytest
from botspool_shared_utils.errors.exceptions import (
    BotsPoolError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    GraphServiceError,
    DatabaseError,
    ExternalServiceError,
    RateLimitError,
    ServerError,
    ConfigurationError,
)
from botspool_shared_utils.errors.error_codes import ErrorCode, ErrorCategory
from botspool_shared_utils.models.enums import ErrorSeverity


class TestBotsPoolError:
    """Test BotsPoolError base exception."""

    def test_bots_pool_error_creation(self):
        """Test that BotsPoolError can be created with basic parameters."""
        error = BotsPoolError("Test error message")

        assert (
            str(error)
            == "[UNKNOWN_ERROR] Test error message (Severity: medium, Category: unknown)"
        )
        assert error.message == "Test error message"
        assert error.error_code is None
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.error_category is None
        assert error.details == {}
        assert error.retryable is False
        assert error.retry_after_seconds is None

    def test_bots_pool_error_with_custom_parameters(self):
        """Test that BotsPoolError can be created with custom parameters."""
        error = BotsPoolError(
            message="Custom error",
            error_code=ErrorCode.AUTH_LOGIN_FAILED_004,
            severity=ErrorSeverity.HIGH,
            error_category=ErrorCategory.AUTHENTICATION,
            details={"field": "password"},
            retryable=True,
            retry_after_seconds=30,
        )

        assert error.message == "Custom error"
        assert error.error_code == ErrorCode.AUTH_LOGIN_FAILED_004
        assert error.severity == ErrorSeverity.HIGH
        assert error.error_category == ErrorCategory.AUTHENTICATION
        assert error.details == {"field": "password"}
        assert error.retryable is True
        assert error.retry_after_seconds == 30

    def test_bots_pool_error_to_dict(self):
        """Test that BotsPoolError can be converted to dictionary."""
        error = BotsPoolError(
            message="Test error",
            error_code=ErrorCode.AUTH_LOGIN_FAILED_004,
            severity=ErrorSeverity.HIGH,
            error_category=ErrorCategory.AUTHENTICATION,
            details={"field": "password"},
        )

        error_dict = error.to_dict()

        assert error_dict["error"]["message"] == "Test error"
        assert error_dict["error"]["code"] == ErrorCode.AUTH_LOGIN_FAILED_004.value
        assert error_dict["error"]["severity"] == ErrorSeverity.HIGH.value
        assert error_dict["error"]["category"] == ErrorCategory.AUTHENTICATION.value
        assert error_dict["error"]["details"] == {"field": "password"}
        assert error_dict["error"]["retryable"] is False
        assert error_dict["error"]["retry_after_seconds"] is None

    def test_bots_pool_error_string_representation(self):
        """Test that BotsPoolError has proper string representation."""
        error = BotsPoolError(
            message="Test error",
            error_code=ErrorCode.AUTH_LOGIN_FAILED_004,
            severity=ErrorSeverity.HIGH,
            error_category=ErrorCategory.AUTHENTICATION,
        )

        error_str = str(error)
        expected = "[AUTH_LOGIN_FAILED_004] Test error (Severity: high, Category: authentication)"

        assert error_str == expected


class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_authentication_error_creation(self):
        """Test that AuthenticationError can be created."""
        error = AuthenticationError(
            message="Invalid credentials", error_code=ErrorCode.AUTH_LOGIN_FAILED_004
        )

        assert error.message == "Invalid credentials"
        assert error.error_code == ErrorCode.AUTH_LOGIN_FAILED_004
        assert error.severity == ErrorSeverity.HIGH
        assert error.error_category == ErrorCategory.AUTHENTICATION
        assert error.retryable is False

    def test_authentication_error_with_details(self):
        """Test that AuthenticationError can include details."""
        error = AuthenticationError(
            message="Token expired",
            error_code=ErrorCode.AUTH_TOKEN_EXPIRED_001,
            details={"expired_at": "2024-01-01T10:00:00Z"},
        )

        assert error.details == {"expired_at": "2024-01-01T10:00:00Z"}


class TestAuthorizationError:
    """Test AuthorizationError exception."""

    def test_authorization_error_creation(self):
        """Test that AuthorizationError can be created."""
        error = AuthorizationError(
            message="Insufficient permissions",
            error_code=ErrorCode.AUTHZ_ACCESS_DENIED_001,
        )

        assert error.message == "Insufficient permissions"
        assert error.error_code == ErrorCode.AUTHZ_ACCESS_DENIED_001
        assert error.severity == ErrorSeverity.HIGH
        assert error.error_category == ErrorCategory.AUTHORIZATION
        assert error.retryable is False


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error_creation(self):
        """Test that ValidationError can be created."""
        error = ValidationError(message="Invalid input format")

        assert error.message == "Invalid input format"
        assert error.error_code == ErrorCode.VALIDATION_INVALID_INPUT_001
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.error_category == ErrorCategory.VALIDATION
        assert error.retryable is False


class TestGraphServiceError:
    """Test GraphServiceError exception."""

    def test_graph_service_error_creation(self):
        """Test that GraphServiceError can be created."""
        error = GraphServiceError(message="Graph execution failed")

        assert error.message == "Graph execution failed"
        assert error.error_code is None
        assert error.severity == ErrorSeverity.HIGH
        assert error.error_category == ErrorCategory.GRAPH
        assert error.retryable is True
        assert error.retry_after_seconds == 5

    def test_graph_service_error_custom_retry(self):
        """Test that GraphServiceError can have custom retry settings."""
        error = GraphServiceError(message="Graph timeout", retry_after_seconds=10)

        assert error.retryable is True
        assert error.retry_after_seconds == 10


class TestDatabaseError:
    """Test DatabaseError exception."""

    def test_database_error_creation(self):
        """Test that DatabaseError can be created."""
        error = DatabaseError(
            message="Connection failed",
            error_code=ErrorCode.DATABASE_CONNECTION_FAILED_001,
        )

        assert error.message == "Connection failed"
        assert error.error_code == ErrorCode.DATABASE_CONNECTION_FAILED_001
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.error_category == ErrorCategory.DATABASE
        assert error.retryable is True
        assert error.retry_after_seconds == 5


class TestExternalServiceError:
    """Test ExternalServiceError exception."""

    def test_external_service_error_creation(self):
        """Test that ExternalServiceError can be created."""
        error = ExternalServiceError(
            message="API call failed",
            service_name="test_service",
            error_code=ErrorCode.EXTERNAL_API_ERROR_001,
        )

        assert error.message == "API call failed"
        assert error.error_code == ErrorCode.EXTERNAL_API_ERROR_001
        assert error.severity == ErrorSeverity.HIGH
        assert error.error_category == ErrorCategory.EXTERNAL_SERVICE
        assert error.retryable is True
        assert error.retry_after_seconds == 5


class TestRateLimitError:
    """Test RateLimitError exception."""

    def test_rate_limit_error_creation(self):
        """Test that RateLimitError can be created."""
        error = RateLimitError(message="Rate limit exceeded", retry_after_seconds=60)

        assert error.message == "Rate limit exceeded"
        assert error.error_code is None
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.error_category == ErrorCategory.RATE_LIMIT
        assert error.retryable is True
        assert error.retry_after_seconds == 60


class TestServerError:
    """Test ServerError exception."""

    def test_server_error_creation(self):
        """Test that ServerError can be created."""
        error = ServerError(message="Internal server error")

        assert error.message == "Internal server error"
        assert error.error_code is None
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.error_category == ErrorCategory.INTERNAL
        assert error.retryable is False


class TestConfigurationError:
    """Test ConfigurationError exception."""

    def test_configuration_error_creation(self):
        """Test that ConfigurationError can be created."""
        error = ConfigurationError(message="Missing configuration")

        assert error.message == "Missing configuration"
        assert error.error_code is None
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.error_category == ErrorCategory.CONFIGURATION
        assert error.retryable is False


class TestExceptionInheritance:
    """Test that all exceptions properly inherit from BotsPoolError."""

    def test_exception_inheritance(self):
        """Test that all custom exceptions inherit from BotsPoolError."""
        exceptions = [
            AuthenticationError,
            AuthorizationError,
            ValidationError,
            GraphServiceError,
            DatabaseError,
            ExternalServiceError,
            RateLimitError,
            ServerError,
            ConfigurationError,
        ]

        for exception_class in exceptions:
            assert issubclass(exception_class, BotsPoolError)

    def test_exception_instantiation(self):
        """Test that all exceptions can be instantiated."""
        exceptions = [
            (AuthenticationError, "Auth error"),
            (AuthorizationError, "Authz error"),
            (ValidationError, "Validation error"),
            (GraphServiceError, "Graph error"),
            (DatabaseError, "DB error"),
            (ExternalServiceError, "External error", "test_service"),
            (RateLimitError, "Rate limit error"),
            (ServerError, "Server error"),
            (ConfigurationError, "Config error"),
        ]

        for exception_data in exceptions:
            if len(exception_data) == 3:
                exception_class, message, service_name = exception_data
                error = exception_class(message, service_name)
            else:
                exception_class, message = exception_data
                error = exception_class(message)
            assert isinstance(error, BotsPoolError)
            assert error.message == message
