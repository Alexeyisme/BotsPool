# Migration Guide

This guide helps you migrate between different versions of `botspool-shared-utils` and provides information about breaking changes, new features, and deprecations.

## Table of Contents
1. [Version 0.1.0 to 0.2.0](#version-010-to-020)
2. [Breaking Changes](#breaking-changes)
3. [New Features](#new-features)
4. [Deprecations](#deprecations)
5. [Migration Steps](#migration-steps)
6. [Troubleshooting](#troubleshooting)

## Version 0.1.0 to 0.2.0

### Overview
Version 0.2.0 introduces several new features and improvements while maintaining backward compatibility for most APIs.

### New Features
- Circuit breaker pattern for resilience
- Retry strategy with exponential backoff
- Graceful degradation mechanisms
- Enhanced health checking
- Improved error context tracking
- Additional OAuth2 providers
- Enhanced MFA support

### Breaking Changes
None in this version - all changes are additive.

### Deprecations
- `ErrorHandler.format_error_response()` - Use `ErrorResponseFormatter` instead
- `DatabaseManager.execute_raw_query()` - Use `execute_query()` instead

## Breaking Changes

### Database Model Changes

#### User Model Restructuring
**Version**: 0.2.0
**Impact**: High

The User model has been restructured to better separate concerns:

**Before:**
```python
from botspool_shared_utils.models import User

user = User(
    email="user@example.com",
    username="john_doe",
    password_hash="hash",
    first_name="John",
    last_name="Doe"
)
```

**After:**
```python
from botspool_shared_utils.models import User, UserAuth, UserProfile

user = User(
    auth=UserAuth(
        email="user@example.com",
        password_hash="hash"
    ),
    profile=UserProfile(
        username="john_doe",
        first_name="John",
        last_name="Doe"
    )
)
```

**Migration Steps:**
1. Update user creation code to use new structure
2. Update database queries to use new model relationships
3. Update serialization/deserialization code

#### Error Code Format Change
**Version**: 0.2.0
**Impact**: Medium

Error codes have been standardized to use a consistent format:

**Before:**
```python
# Inconsistent error codes
"TOKEN_EXPIRED"
"GRAPH_UNAVAILABLE"
"DB_CONNECTION_FAILED"
```

**After:**
```python
# Standardized error codes
"AUTH_TOKEN_EXPIRED_001"
"GRAPH_SERVICE_UNAVAILABLE_001"
"DATABASE_CONNECTION_FAILED_001"
```

**Migration Steps:**
1. Update error handling code to use new error codes
2. Update error logging and monitoring
3. Update API responses and documentation

### Authentication Changes

#### JWT Payload Structure
**Version**: 0.2.0
**Impact**: Medium

JWT payload structure has been updated to include additional fields:

**Before:**
```json
{
  "sub": "user_id",
  "iss": "botspool.ai",
  "aud": "botspool-api",
  "iat": 1640995200,
  "exp": 1641081600,
  "role": "premium_user"
}
```

**After:**
```json
{
  "sub": "user_id",
  "iss": "botspool.ai",
  "aud": "botspool-api",
  "iat": 1640995200,
  "exp": 1641081600,
  "type": "access",
  "role": "premium_user",
  "permissions": ["read_graphs", "write_graphs"],
  "jti": "unique_token_id"
}
```

**Migration Steps:**
1. Update JWT validation code to handle new fields
2. Update token refresh logic
3. Update client-side token handling

#### Session Management API Changes
**Version**: 0.2.0
**Impact**: Low

Session management methods have been updated for better consistency:

**Before:**
```python
# Old method names
session_manager.create_user_session()
session_manager.get_user_session()
session_manager.delete_user_session()
```

**After:**
```python
# New method names
session_manager.create_session()
session_manager.get_session()
session_manager.delete_session()
```

**Migration Steps:**
1. Update method calls to use new names
2. Update parameter names if changed
3. Update error handling for new exceptions

#### Durable Session Service
**Version**: 0.3.0
**Impact**: Medium

Session persistence now lives in Postgres with Redis used as a write-through cache. The new `SessionService` supersedes the Redis-only `SessionManager` helpers.

**Before:**
```python
session_manager = create_session_manager(redis_client)
await session_manager.create_session(session_id, user_id)
```

**After:**
```python
from botspool_shared_utils.sessions import SessionService, SessionSettings
from botspool_shared_utils.models import SessionCreate, FrontendType

service = SessionService(db_manager, redis_manager, SessionSettings.from_env())
await service.start_session(
    SessionCreate(frontend_type=FrontendType.TELEGRAM, chat_id="123", user_id=user_id)
)
```

**Migration Steps:**
1. Ensure the new `session_records` migration is applied.
2. Instantiate `SessionService` with both database and Redis managers (Redis optional but recommended).
3. Replace `SessionManager` calls with `SessionService` equivalents (`start_session`, `get_session`, `update_session`, `clear_session`).
4. Configure session TTLs via `SESSION_DEFAULT_TTL_SECONDS` / `SESSION_CACHE_TTL_SECONDS` environment variables if custom values are required.

## New Features

### Circuit Breaker Pattern
**Version**: 0.2.0

New circuit breaker implementation for improved resilience:

```python
from botspool_shared_utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60
)

circuit_breaker = CircuitBreaker("external_service", config)

# Use circuit breaker
try:
    result = await circuit_breaker.call(external_service_call, param1, param2)
except CircuitBreakerOpenError:
    # Handle circuit breaker open
    pass
```

### Retry Strategy
**Version**: 0.2.0

Exponential backoff retry mechanism:

```python
from botspool_shared_utils.retry import RetryManager, RetryConfig

config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0
)

retry_manager = RetryManager(config)

# Use retry manager
result = await retry_manager.retry_async(risky_operation, param1, param2)
```

### Enhanced Error Context
**Version**: 0.2.0

Improved error context tracking:

```python
from botspool_shared_utils.errors import ErrorContext, add_error_context

# Create rich error context
context = ErrorContext(
    request_id="req_123",
    user_id="user_456",
    session_id="session_789",
    conversation_id="conv_101",
    graph_type="todo",
    frontend_type="telegram",
    ip_address="192.168.1.1",
    user_agent="TelegramBot/1.0",
    endpoint="/api/v1/chat/todo",
    method="POST"
)

# Add context to exception
try:
    risky_operation()
except Exception as e:
    add_error_context(e, context)
    raise
```

### Additional OAuth2 Providers
**Version**: 0.2.0

Support for additional OAuth2 providers:

```python
from botspool_shared_utils.auth import register_microsoft_provider, register_slack_provider

# Register Microsoft provider
register_microsoft_provider(
    client_id="microsoft_client_id",
    client_secret="microsoft_client_secret",
    redirect_uri="https://app.example.com/auth/microsoft/callback"
)

# Register Slack provider
register_slack_provider(
    client_id="slack_client_id",
    client_secret="slack_client_secret",
    redirect_uri="https://app.example.com/auth/slack/callback"
)
```

## Deprecations

### Deprecated APIs

#### ErrorHandler.format_error_response()
**Deprecated in**: 0.2.0
**Removed in**: 0.3.0
**Replacement**: `ErrorResponseFormatter`

**Before:**
```python
from botspool_shared_utils.errors import ErrorHandler

handler = ErrorHandler()
response = handler.format_error_response(error, context)
```

**After:**
```python
from botspool_shared_utils.errors import ErrorResponseFormatter

response = ErrorResponseFormatter.format_for_api(error, context)
```

#### DatabaseManager.execute_raw_query()
**Deprecated in**: 0.2.0
**Removed in**: 0.3.0
**Replacement**: `execute_query()`

**Before:**
```python
result = await db_manager.execute_raw_query("SELECT * FROM users")
```

**After:**
```python
result = await db_manager.execute_query("SELECT * FROM users")
```

### Deprecated Configuration Options

#### JWT Handler Configuration
**Deprecated in**: 0.2.0
**Removed in**: 0.3.0

**Before:**
```python
jwt_handler = JWTHandler(
    private_key=private_key,
    public_key=public_key,
    access_token_lifetime=3600,  # Deprecated
    refresh_token_lifetime=2592000  # Deprecated
)
```

**After:**
```python
jwt_handler = JWTHandler(
    private_key=private_key,
    public_key=public_key,
    access_token_expiry=3600,  # New name
    refresh_token_expiry=2592000  # New name
)
```

## Migration Steps

### Step 1: Update Dependencies
```bash
pip install --upgrade botspool-shared-utils>=0.2.0
```

### Step 2: Update Imports
```python
# Update imports for new modules
from botspool_shared_utils.circuit_breaker import CircuitBreaker
from botspool_shared_utils.retry import RetryManager
from botspool_shared_utils.errors import ErrorResponseFormatter
```

### Step 3: Update Error Handling
```python
# Replace deprecated error handling
# Before
from botspool_shared_utils.errors import ErrorHandler
handler = ErrorHandler()
response = handler.format_error_response(error, context)

# After
from botspool_shared_utils.errors import ErrorResponseFormatter
response = ErrorResponseFormatter.format_for_api(error, context)
```

### Step 4: Update Database Operations
```python
# Replace deprecated database methods
# Before
result = await db_manager.execute_raw_query("SELECT * FROM users")

# After
result = await db_manager.execute_query("SELECT * FROM users")
```

### Step 5: Update JWT Configuration
```python
# Update JWT handler configuration
# Before
jwt_handler = JWTHandler(
    access_token_lifetime=3600,
    refresh_token_lifetime=2592000
)

# After
jwt_handler = JWTHandler(
    access_token_expiry=3600,
    refresh_token_expiry=2592000
)
```

### Step 6: Update User Model Usage
```python
# Update user model structure
# Before
user = User(
    email="user@example.com",
    username="john_doe",
    password_hash="hash"
)

# After
user = User(
    auth=UserAuth(
        email="user@example.com",
        password_hash="hash"
    ),
    profile=UserProfile(
        username="john_doe"
    )
)
```

### Step 7: Add Circuit Breaker (Optional)
```python
# Add circuit breaker for external services
from botspool_shared_utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60
)

circuit_breaker = CircuitBreaker("external_service", config)

# Wrap external service calls
result = await circuit_breaker.call(external_service_call, param1, param2)
```

### Step 8: Add Retry Logic (Optional)
```python
# Add retry logic for transient failures
from botspool_shared_utils.retry import RetryManager, RetryConfig

config = RetryConfig(
    max_attempts=3,
    base_delay=1.0
)

retry_manager = RetryManager(config)

# Wrap risky operations
result = await retry_manager.retry_async(risky_operation, param1, param2)
```

### Step 9: Update Tests
```python
# Update test code to use new APIs
def test_error_handling():
    # Before
    handler = ErrorHandler()
    response = handler.format_error_response(error, context)
    
    # After
    response = ErrorResponseFormatter.format_for_api(error, context)
    assert response["error"]["code"] == "AUTH_TOKEN_EXPIRED_001"
```

### Step 10: Update Documentation
- Update API documentation
- Update code examples
- Update error code references
- Update configuration documentation

## Troubleshooting

### Common Issues

#### Import Errors
**Problem**: Import errors after upgrade
**Solution**: Check import paths and update to new module structure

```python
# Check if imports are correct
from botspool_shared_utils.errors import ErrorResponseFormatter  # Correct
from botspool_shared_utils.errors import ErrorHandler  # May be deprecated
```

#### Database Migration Issues
**Problem**: Database schema conflicts
**Solution**: Run database migrations

```bash
# Run migrations
alembic upgrade head
```

#### JWT Token Validation Errors
**Problem**: JWT tokens not validating
**Solution**: Check token structure and update validation code

```python
# Ensure JWT payload includes new fields
payload = jwt_handler.validate_token(token, "access")
assert "type" in payload
assert "permissions" in payload
```

#### Session Management Errors
**Problem**: Session operations failing
**Solution**: Update method calls to use new API

```python
# Use new method names
session = await session_manager.get_session(session_id)  # Correct
session = await session_manager.get_user_session(session_id)  # Deprecated
```

### Getting Help

If you encounter issues during migration:

1. **Check the Changelog**: Review the changelog for detailed changes
2. **Review API Reference**: Check the API reference for correct usage
3. **Run Tests**: Ensure all tests pass after migration
4. **Check Logs**: Review error logs for specific issues
5. **Contact Support**: Reach out to the development team for assistance

### Rollback Plan

If migration fails:

1. **Revert Dependencies**: Downgrade to previous version
```bash
pip install botspool-shared-utils==0.1.0
```

2. **Revert Code Changes**: Restore previous code version
3. **Run Tests**: Ensure system works with previous version
4. **Plan Migration**: Review migration steps and try again

### Performance Considerations

After migration:

1. **Monitor Performance**: Check for performance regressions
2. **Update Monitoring**: Update monitoring to track new metrics
3. **Optimize Configuration**: Tune new configuration options
4. **Review Logs**: Check for new error patterns
