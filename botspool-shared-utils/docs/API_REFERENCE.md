# API Reference

This document provides a comprehensive reference for all public APIs in the `botspool-shared-utils` package.

## Table of Contents
1. [Models](#models)
2. [Error Handling](#error-handling)
3. [Database](#database)
4. [Authentication](#authentication)
5. [Encryption](#encryption)
6. [Logging](#logging)
7. [Validation](#validation)
8. [PII Anonymization](#pii-anonymization)
9. [Service Interfaces](#service-interfaces)
10. [Utilities](#utilities)
    - [LangGraph Helpers](#langgraph-helpers)
    - [Gateway Registration](#gateway-registration)
    - [Notification Toolset](#notification-toolset)
    - [Session Service](#session-service)

## Models

### Base Models

#### BaseModel
Base class for all Pydantic models with common configuration.

```python
from botspool_shared_utils.models import BaseModel

class MyModel(BaseModel):
    field: str
```

#### TimestampMixin
Adds `created_at` and `updated_at` timestamp fields.

```python
from botspool_shared_utils.models import TimestampMixin

class MyModel(TimestampMixin):
    name: str
```

#### MetadataMixin
Adds flexible `metadata` field for additional data.

```python
from botspool_shared_utils.models import MetadataMixin

class MyModel(MetadataMixin):
    data: str
```

### User Models

#### User
Main user entity combining authentication, profile, and preferences.

```python
from botspool_shared_utils.models import User, UserAuth, UserProfile, UserPreferences
from botspool_shared_utils.enums import UserRole, SubscriptionTier, AuthProvider

user = User(
    auth=UserAuth(
        provider=AuthProvider.EMAIL,
        email="user@example.com",
        password_hash="hashed_password"
    ),
    profile=UserProfile(
        username="john_doe",
        first_name="John",
        last_name="Doe"
    ),
    preferences=UserPreferences(),
    role=UserRole.FREE_USER,
    subscription_tier=SubscriptionTier.FREE
)
```

#### UserCreate
Model for creating a new user.

```python
from botspool_shared_utils.models import UserCreate

user_data = UserCreate(
    email="user@example.com",
    username="john_doe",
    password="SecurePassword123!",
    first_name="John",
    last_name="Doe"
)
```

#### UserUpdate
Model for updating user information.

```python
from botspool_shared_utils.models import UserUpdate

update_data = UserUpdate(
    first_name="Jane",
    last_name="Smith",
    bio="Updated bio"
)
```

### Chat Models

#### ChatRequest
Incoming chat request from frontends.

```python
from botspool_shared_utils.models import ChatRequest, ChatContext
from botspool_shared_utils.enums import FrontendType

request = ChatRequest(
    message="Hello, world!",
    user_id="user_123",
    frontend_type=FrontendType.TELEGRAM,
    context=ChatContext(
        current_bot="todo",
        user_preferences={"theme": "dark"}
    )
)
```

#### ChatResponse
Response from AI graphs to frontends.

```python
from botspool_shared_utils.models import ChatResponse
from botspool_shared_utils.enums import GraphType

response = ChatResponse(
    response="Hello! How can I help you?",
    graph_type=GraphType.TODO,
    user_id="user_123",
    session_id="session_456",
    processing_time=1.5,
    tokens_used=150
)
```

#### ChatSession
Chat conversation session with context and history.

```python
from botspool_shared_utils.models import ChatSession, ChatContext
from botspool_shared_utils.enums import FrontendType, ChatStatus, GraphType

session = ChatSession(
    user_id="user_123",
    session_id="session_456",
    frontend_type=FrontendType.TELEGRAM,
    status=ChatStatus.ACTIVE,
    context=ChatContext(),
    current_graph=GraphType.TODO
)
```

### Subscription Models

#### Subscription
User's subscription with plan and usage tracking.

```python
from botspool_shared_utils.models import Subscription, SubscriptionPlan, UsageTracking
from botspool_shared_utils.enums import SubscriptionTier

subscription = Subscription(
    user_id="user_123",
    plan=SubscriptionPlan(
        tier=SubscriptionTier.PREMIUM,
        name="Premium Plan",
        price_monthly=2999,  # $29.99 in cents
        limits=UsageLimit(
            requests_per_day=5000,
            tokens_per_day=100000,
            allowed_graphs=[GraphType.TODO, GraphType.EMAIL, GraphType.CALENDAR]
        )
    ),
    usage=UsageTracking(
        user_id="user_123",
        subscription_tier=SubscriptionTier.PREMIUM
    )
)
```

### Graph Models

#### Graph
AI graph definition with instances and configuration.

```python
from botspool_shared_utils.models import Graph, GraphConfig
from botspool_shared_utils.enums import GraphType, GraphStatus

graph = Graph(
    graph_type=GraphType.TODO,
    name="ToDo Assistant",
    description="Task management assistant",
    version="1.0.0",
    author="BotsPool Team",
    status=GraphStatus.HEALTHY,
    is_available=True,
    default_config=GraphConfig(
        model_name="gpt-4",
        temperature=0.7,
        max_tokens=1000
    )
)
```

## Error Handling

### Exception Classes

#### BotsPoolError
Base exception class for all BotsPool errors.

```python
from botspool_shared_utils.errors import BotsPoolError, ErrorCode, ErrorCategory

error = BotsPoolError(
    message="Something went wrong",
    error_code=ErrorCode.INTERNAL_SERVER_ERROR_001,
    error_category=ErrorCategory.INTERNAL,
    user_id="user_123",
    retryable=True,
    retry_after=30
)
```

#### AuthenticationError
Authentication-related errors.

```python
from botspool_shared_utils.errors import AuthenticationError, TokenExpiredError

# Token expired
try:
    validate_token(expired_token)
except TokenExpiredError as e:
    print(f"Token expired: {e.message}")
```

#### ValidationError
Input validation errors.

```python
from botspool_shared_utils.errors import ValidationError

try:
    validate_input(invalid_data)
except ValidationError as e:
    print(f"Validation failed: {e.message}")
    print(f"Field: {e.details.get('field')}")
```

### Error Handling Utilities

#### ErrorHandler
Centralized error handling.

```python
from botspool_shared_utils.errors import ErrorHandler, ErrorContext

handler = ErrorHandler()

# Handle error with context
context = ErrorContext(
    request_id="req_123",
    user_id="user_456",
    frontend_type="telegram"
)

error_response = handler.handle_error(error, context)
```

#### Error Context
Rich error context information.

```python
from botspool_shared_utils.errors import ErrorContext, create_error_context

# Create error context
context = create_error_context(
    request_id="req_123",
    user_id="user_456",
    frontend_type="telegram",
    ip_address="192.168.1.1",
    user_agent="TelegramBot/1.0"
)

# Add additional data
context.add_data("graph_type", "todo")
context.add_data("session_id", "session_789")
```

## Database

### Connection Management

#### DatabaseManager
Database connection manager.

```python
from botspool_shared_utils.database import DatabaseManager, create_connection_pool

# Create connection pool
db_manager = await create_connection_pool(
    database_url="postgresql://user:pass@localhost/db",
    pool_size=10,
    max_overflow=20
)

# Get session
async with db_manager.get_session_context() as session:
    # Use session
    pass

# Execute query
result = await db_manager.execute_query(
    "SELECT * FROM users WHERE email = :email",
    {"email": "user@example.com"}
)
```

### Query Utilities

#### UserQueries
User-related database queries.

```python
from botspool_shared_utils.database import UserQueries

async with db_manager.get_session_context() as session:
    user_queries = UserQueries(session)
    
    # Get user by email
    user = await user_queries.get_user_by_email("user@example.com")
    
    # Create user
    new_user = await user_queries.create_user({
        "email": "new@example.com",
        "username": "new_user"
    })
    
    # Update user
    updated_user = await user_queries.update_user(
        user.id, 
        {"first_name": "Updated"}
    )
```

#### ChatQueries
Chat-related database queries.

```python
from botspool_shared_utils.database import ChatQueries

async with db_manager.get_session_context() as session:
    chat_queries = ChatQueries(session)
    
    # Get chat session
    session = await chat_queries.get_chat_session_by_id("session_123")
    
    # Add message
    message = await chat_queries.add_chat_message({
        "session_id": "session_123",
        "user_id": "user_456",
        "message_type": "user",
        "content": "Hello!"
    })
    
    # Get chat history
    messages = await chat_queries.get_chat_messages("session_123", limit=50)
```

### ORM Models

#### UserModel
SQLAlchemy model for users.

```python
from botspool_shared_utils.database.models import UserModel, UserAuthModel, UserProfileModel

# Query users
from sqlalchemy import select

async with db_manager.get_session_context() as session:
    result = await session.execute(
        select(UserModel)
        .join(UserAuthModel)
        .where(UserAuthModel.email == "user@example.com")
    )
    user = result.scalar_one_or_none()
```

## Authentication

### JWT Management

#### JWTHandler
JWT token management.

```python
from botspool_shared_utils.auth import JWTHandler, create_jwt_handler
from botspool_shared_utils.enums import UserRole, Permission

# Create JWT handler
jwt_handler = create_jwt_handler(
    private_key="-----BEGIN PRIVATE KEY-----...",
    public_key="-----BEGIN PUBLIC KEY-----...",
    access_token_expiry=3600,
    refresh_token_expiry=2592000
)

# Generate access token
access_token = jwt_handler.generate_access_token(
    user_id="user_123",
    role=UserRole.PREMIUM_USER,
    permissions=[Permission.READ_GRAPHS, Permission.WRITE_GRAPHS]
)

# Generate refresh token
refresh_token = jwt_handler.generate_refresh_token("user_123")

# Validate token
payload = jwt_handler.validate_token(access_token, "access")

# Refresh token
new_tokens = jwt_handler.refresh_access_token(refresh_token)
```

### Password Management

#### PasswordManager
Password security utilities.

```python
from botspool_shared_utils.auth import PasswordManager, hash_password, verify_password

# Hash password
password_hash = hash_password("SecurePassword123!")

# Verify password
is_valid = verify_password("SecurePassword123!", password_hash)

# Generate secure password
from botspool_shared_utils.auth import get_password_manager
manager = get_password_manager()
secure_password = manager.generate_secure_password(length=16)
```

### RBAC (Role-Based Access Control)

#### RBACManager
Role-based access control.

```python
from botspool_shared_utils.auth import RBACManager, get_rbac_manager
from botspool_shared_utils.enums import UserRole, Permission, GraphType

rbac = get_rbac_manager()

# Check permission
has_permission = rbac.check_permission(
    UserRole.PREMIUM_USER, 
    Permission.READ_GRAPHS
)

# Check graph access
can_access = rbac.check_graph_access(
    UserRole.PREMIUM_USER, 
    GraphType.TODO
)

# Get user permissions
permissions = rbac.get_user_permissions(UserRole.PREMIUM_USER)

# Require permission (raises exception if not authorized)
rbac.require_permission(UserRole.FREE_USER, Permission.ADMIN_GRAPHS)
```

### Multi-Factor Authentication

#### MFAHandler
Multi-factor authentication.

```python
from botspool_shared_utils.auth import MFAHandler, get_mfa_handler

mfa = get_mfa_handler()

# Generate MFA secret
secret = mfa.generate_secret("user_123")

# Generate QR code
qr_code = mfa.generate_qr_code(
    user_id="user_123",
    secret=secret,
    user_email="user@example.com"
)

# Verify MFA token
is_valid = mfa.verify_token(secret, "123456")

# Generate backup codes
backup_codes = mfa.generate_backup_codes(count=10)
```

### OAuth2 Integration

#### OAuthManager
OAuth2 authentication.

```python
from botspool_shared_utils.auth import OAuthManager, register_google_provider

# Register OAuth providers
register_google_provider(
    client_id="google_client_id",
    client_secret="google_client_secret",
    redirect_uri="https://app.example.com/auth/google/callback"
)

# Get OAuth manager
oauth_manager = get_oauth_manager()

# Get authorization URL
auth_url = oauth_manager.get_authorization_url("google", "state_123")

# Authenticate user
user_info = await oauth_manager.authenticate_user("google", "auth_code")
```

### Session Management

#### Session Service
Durable session storage backed by Postgres with Redis caching.

```python
from datetime import timedelta
from botspool_shared_utils.database import get_database_manager
from botspool_shared_utils.redis_utils import get_redis_manager_shared
from botspool_shared_utils.models import SessionCreate, SessionUpdate, FrontendType
from botspool_shared_utils.sessions import SessionService, SessionSettings

# Initialise shared infrastructure
db_manager = get_database_manager()
redis_manager = await get_redis_manager_shared()

# Build the session service (defaults enable Redis caching)
settings = SessionSettings.from_env()
session_service = SessionService(db_manager, redis_manager, settings)

# Create or refresh a session
session_record = await session_service.start_session(
    SessionCreate(
        frontend_type=FrontendType.TELEGRAM,
        chat_id="123456789",
        user_id=None,
        current_agent="todo",
        locale="ru",
        state_payload={"menu": "main"},
        expires_at=None,
    )
)

# Read session state (serves from Redis cache when available)
session = await session_service.get_session(FrontendType.TELEGRAM, "123456789")

# Update session metadata
await session_service.update_session(
    FrontendType.TELEGRAM,
    "123456789",
    SessionUpdate(
        current_agent="planner",
        expires_at=session.expires_at + timedelta(hours=1) if session.expires_at else None,
    ),
)

# Clear session when it should be removed
await session_service.clear_session(FrontendType.TELEGRAM, "123456789")
```

## Encryption

### Core Encryption Functions

#### encrypt_data
Encrypt data using AES-256-GCM.

```python
from botspool_shared_utils.encryption import encrypt_data, decrypt_data, generate_encryption_key

# Generate encryption key
key = generate_encryption_key()

# Encrypt data
data = "sensitive information"
encrypted_data, iv, auth_tag = encrypt_data(data, key)

# Decrypt data
decrypted_data = decrypt_data(encrypted_data, key, iv, auth_tag)
```

#### encrypt_field / decrypt_field
Encrypt/decrypt individual fields with base64 encoding.

```python
from botspool_shared_utils.encryption import encrypt_field, decrypt_field

# Encrypt a field
email = "user@example.com"
encrypted_email = encrypt_field(email, key)

# Decrypt the field
decrypted_email = decrypt_field(encrypted_email, key)
```

#### generate_key_pair
Generate RSA key pairs for asymmetric encryption.

```python
from botspool_shared_utils.encryption import generate_key_pair, encrypt_with_public_key, decrypt_with_private_key

# Generate key pair
private_key, public_key = generate_key_pair()

# Encrypt with public key
data = "sensitive data"
encrypted_data = encrypt_with_public_key(data, public_key)

# Decrypt with private key
decrypted_data = decrypt_with_private_key(encrypted_data, private_key)
```

### Key Management

#### KeyManager
Manage encryption keys with secure storage and rotation.

```python
from botspool_shared_utils.encryption import KeyManager

# Initialize key manager
key_manager = KeyManager(storage_path="keys.json")

# Generate and store key
key = key_manager.generate_secure_key("user-encryption", "aes")

# Retrieve key
retrieved_key = key_manager.retrieve_key("user-encryption")

# Rotate key
new_key = key_manager.rotate_key("user-encryption")
```

## Logging

### Logging Configuration

#### setup_logging
Configure logging for different environments.

```python
from botspool_shared_utils.logging import setup_logging

# Development logging
setup_logging(
    level="DEBUG",
    environment="development",
    log_file="app.log"
)

# Production logging
setup_logging(
    level="INFO",
    environment="production",
    log_file="/var/log/app.log",
    log_dir="/var/log"
)
```

#### get_logger
Get a logger instance for your module.

```python
from botspool_shared_utils.logging import get_logger

logger = get_logger(__name__)
logger.info("Application started")
logger.warning("This is a warning")
logger.error("An error occurred")
```

### Log Formatters

#### JSONFormatter
Structured JSON logging for production.

```python
from botspool_shared_utils.logging import JSONFormatter

formatter = JSONFormatter()
# Automatically used in production logging setup
```

#### HumanReadableFormatter
Human-readable logging for development.

```python
from botspool_shared_utils.logging import HumanReadableFormatter

formatter = HumanReadableFormatter()
# Automatically used in development logging setup
```

## Validation

### Input Validators

#### validate_email
Validate email address format.

```python
from botspool_shared_utils.validation import validate_email

is_valid = validate_email("user@example.com")  # True
is_valid = validate_email("invalid-email")     # False
```

#### validate_password
Validate password strength with detailed feedback.

```python
from botspool_shared_utils.validation import validate_password

result = validate_password("MySecure123!", min_length=8)
print(result["valid"])  # True
print(result["errors"]) # []
```

#### validate_username
Validate username format.

```python
from botspool_shared_utils.validation import validate_username

is_valid = validate_username("john_doe")  # True
is_valid = validate_username("john-doe")  # False (contains hyphen)
```

### Data Sanitizers

#### sanitize_string
Sanitize strings by removing dangerous characters.

```python
from botspool_shared_utils.validation import sanitize_string

# Basic sanitization
clean_string = sanitize_string("Hello\x00World")

# With character filter
clean_string = sanitize_string("Hello123", allowed_chars="a-zA-Z")

# With length limit
clean_string = sanitize_string("Very long string", max_length=10)
```

#### sanitize_html
Sanitize HTML content to prevent XSS.

```python
from botspool_shared_utils.validation import sanitize_html

# Escape all HTML
safe_html = sanitize_html("<script>alert('xss')</script>")

# Allow specific tags
safe_html = sanitize_html(
    "<p>Hello <b>world</b></p>",
    allowed_tags=["p", "b", "i"]
)
```

## PII Anonymization

### PII Detection

#### detect_pii
Detect PII in text data.

```python
from botspool_shared_utils.anonymization import detect_pii

text = "Contact John Doe at john.doe@example.com or call (555) 123-4567"
detected_pii = detect_pii(text)

for pii in detected_pii:
    print(f"Found {pii['pii_type']}: {pii['value']}")
    print(f"Confidence: {pii['confidence']}")
```

#### detect_email / detect_phone
Detect specific types of PII.

```python
from botspool_shared_utils.anonymization import detect_email, detect_phone

emails = detect_email("Contact us at support@example.com")
phones = detect_phone("Call us at (555) 123-4567")
```

### Data Anonymization

#### anonymize_email
Anonymize email addresses.

```python
from botspool_shared_utils.anonymization import anonymize_email

original = "john.doe@example.com"
anonymized = anonymize_email(original)
print(anonymized)  # "***@example.com"
```

#### anonymize_phone
Anonymize phone numbers.

```python
from botspool_shared_utils.anonymization import anonymize_phone

original = "(555) 123-4567"
anonymized = anonymize_phone(original)
print(anonymized)  # "***-***-4567"
```

#### mask_data
Mask sensitive data with configurable options.

```python
from botspool_shared_utils.anonymization import mask_data

# Preserve length
masked = mask_data("1234567890", preserve_length=True)
print(masked)  # "**********"

# Show first and last characters
masked = mask_data("1234567890", preserve_length=False)
print(masked)  # "1********0"
```

## Service Interfaces

### Base Interfaces

#### ServiceInterface
Abstract base class for all services.

```python
from botspool_shared_utils.interfaces import ServiceInterface

class MyService(ServiceInterface):
    async def initialize(self) -> None:
        # Initialize service
        pass
    
    async def shutdown(self) -> None:
        # Shutdown service
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        # Return health status
        return {"status": "healthy"}
    
    @property
    def is_healthy(self) -> bool:
        return True
```

#### RepositoryInterface
Abstract base class for repositories.

```python
from botspool_shared_utils.interfaces import RepositoryInterface

class UserRepository(RepositoryInterface[User, str]):
    async def create(self, entity: User) -> User:
        # Create user
        pass
    
    async def get_by_id(self, entity_id: str) -> Optional[User]:
        # Get user by ID
        pass
    
    async def update(self, entity: User) -> User:
        # Update user
        pass
    
    async def delete(self, entity_id: str) -> bool:
        # Delete user
        pass
```

## Utilities

### Circuit Breaker

#### CircuitBreaker
Implement circuit breaker pattern for resilience.

```python
from botspool_shared_utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

# Configure circuit breaker
config = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=3
)

# Create circuit breaker
circuit_breaker = CircuitBreaker("my-service", config)

# Use with async function
@circuit_breaker
async def risky_operation():
    # Your risky operation here
    pass

# Or call directly
result = await circuit_breaker.call(risky_operation)
```

### Retry Strategy

#### RetryManager
Implement retry strategies with exponential backoff.

```python
from botspool_shared_utils.retry import RetryManager, RetryConfig

# Configure retry strategy
config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0
)

# Create retry manager
retry_manager = RetryManager(config)

# Use with async function
@retry_manager.retry
async def unreliable_operation():
    # Your unreliable operation here
    pass

# Or call directly
result = await retry_manager.retry_async(unreliable_operation)
```

### Redis Utilities

#### RedisManager
Redis connection and operation management.

```python
from botspool_shared_utils.redis_utils import RedisManager

# Initialize Redis manager
redis_manager = RedisManager(redis_url="redis://localhost:6379")

# Session management
await redis_manager.store_session("session_123", {"user_id": "user_456"})
session_data = await redis_manager.get_session("session_123")
await redis_manager.delete_session("session_123")

# Pool registry
await redis_manager.register_instance("todo", "instance-1", "http://todo-1:8000")
instances = await redis_manager.get_instances("todo")
await redis_manager.unregister_instance("todo", "instance-1")

# Usage tracking
await redis_manager.track_usage("user_123", "api_calls", 1)
usage = await redis_manager.get_usage("user_123", "api_calls")
```

### LangGraph Helpers

#### PostgreSQL Checkpointer Factory
Create and manage LangGraph-compatible PostgreSQL checkpointers.

```python
from botspool_shared_utils.langgraph import (
    create_postgres_checkpointer,
    close_postgres_checkpointer,
)

async def build_checkpointer(database_url: str):
    checkpointer = await create_postgres_checkpointer(database_url)
    try:
        # Use the checkpointer with your LangGraph application
        return checkpointer
    finally:
        await close_postgres_checkpointer(checkpointer)
```

### Gateway Registration

#### GatewayRegistrationService
Register graph instances with the BotsPool gateway using a resilient heartbeat.

```python
from botspool_shared_utils.gateway import (
    GatewayRegistrationService,
    RegistrationConfig,
)
from botspool_shared_utils.models.enums import GraphType

config = RegistrationConfig(
    gateway_url="http://gateway:8000",
    register_endpoint="/api/v1/graphs/register",
    instance_id="todo-001",
    graph_type=GraphType.TODO,
    endpoint="http://todo-graph:8001",
    capacity=100,
    version="1.0.0",
    interval_seconds=30,
)

service = GatewayRegistrationService(config)
await service.start()
# ... application runs ...
await service.stop()
```

### Notification Toolset

#### NotificationClientConfig and create_notification_toolset
Create LangChain-compatible notification tools with environment-aware configuration.

```python
from botspool_shared_utils.notifications import (
    NotificationClientConfig,
    create_notification_toolset,
)

config = NotificationClientConfig.from_env(agent="todo", frontend="telegram")
toolset = create_notification_toolset(config)

# LangChain tools for LLMs
send_notification = toolset.send_notification
schedule_reminder = toolset.schedule_reminder

# Direct implementations for non-LLM usage
result = await toolset.send_notification_impl(
    message="Task completed",
    chat_id=12345,
    user_id="user-abc",
)

reminder = await toolset.schedule_reminder_impl(
    message="Follow up in 1 hour",
    hours_from_now=1,
    chat_id=12345,
    user_id="user-abc",
)
```

### Error Handling Utilities

#### Format Error Response
Format errors for API responses.

```python
from botspool_shared_utils.errors import format_error_response, ErrorResponseFormatter

# Format for development
dev_response = ErrorResponseFormatter.format_for_development(error, context)

# Format for production
prod_response = ErrorResponseFormatter.format_for_production(error, context)

# Format for API
api_response = ErrorResponseFormatter.format_for_api(error, context)
```

#### Log Error
Log errors with appropriate level and context.

```python
from botspool_shared_utils.errors import log_error

log_error(
    error=error,
    context=context,
    include_traceback=True,
    logger=logger
)
```

### Database Utilities

#### Migration Management
Database migration utilities.

```python
from botspool_shared_utils.database import run_migrations, create_migration

# Run migrations
await run_migrations(db_manager, target_revision="head")

# Create migration
migration_id = await create_migration(
    db_manager,
    message="Add user preferences table",
    autogenerate=True
)
```

#### Database Monitoring
Database monitoring utilities.

```python
from botspool_shared_utils.database import DatabaseMonitor

monitor = DatabaseMonitor(db_manager)

# Start monitoring
await monitor.start_monitoring()

# Get comprehensive status
status = await monitor.get_comprehensive_status()

# Stop monitoring
await monitor.stop_monitoring()
```

### Authentication Utilities

#### Auth Service
Unified authentication service.

```python
from botspool_shared_utils.auth import AuthService, get_auth_service
from botspool_shared_utils.enums import FrontendType

auth_service = get_auth_service()

# Authenticate user
result = await auth_service.authenticate_user(
    email="user@example.com",
    password="password",
    frontend_type=FrontendType.TELEGRAM
)

# Authorize user
is_authorized = await auth_service.authorize_user(
    UserRole.PREMIUM_USER,
    Permission.READ_GRAPHS
)

# Create user session
session_id = await auth_service.create_user_session(
    user_id="user_123",
    frontend_type=FrontendType.TELEGRAM
)
```

## Enums Reference

### SubscriptionTier
```python
from botspool_shared_utils.enums import SubscriptionTier

SubscriptionTier.FREE        # Free tier
SubscriptionTier.BASIC       # Basic tier
SubscriptionTier.PREMIUM     # Premium tier
SubscriptionTier.ENTERPRISE  # Enterprise tier
```

### GraphType
```python
from botspool_shared_utils.enums import GraphType

GraphType.TODO       # ToDo assistant
GraphType.EMAIL      # Email assistant
GraphType.CALENDAR   # Calendar assistant
GraphType.DOCUMENT   # Document assistant
GraphType.CODE       # Code assistant
GraphType.RESEARCH   # Research assistant
```

### UserRole
```python
from botspool_shared_utils.enums import UserRole

UserRole.FREE_USER        # Free user
UserRole.BASIC_USER       # Basic user
UserRole.PREMIUM_USER     # Premium user
UserRole.ENTERPRISE_USER  # Enterprise user
UserRole.ADMIN            # Administrator
UserRole.DEVELOPER        # Developer
```

### Permission
```python
from botspool_shared_utils.enums import Permission

Permission.READ_GRAPHS           # Read graph access
Permission.WRITE_GRAPHS          # Write graph access
Permission.ADMIN_GRAPHS          # Admin graph access
Permission.MANAGE_USERS          # Manage users
Permission.VIEW_ANALYTICS        # View analytics
Permission.MANAGE_SUBSCRIPTIONS  # Manage subscriptions
Permission.SYSTEM_ADMIN          # System administration
Permission.VIEW_LOGS             # View logs
Permission.MANAGE_INFRASTRUCTURE # Manage infrastructure
```

### FrontendType
```python
from botspool_shared_utils.enums import FrontendType

FrontendType.TELEGRAM  # Telegram bot
FrontendType.DISCORD   # Discord bot
FrontendType.WEB       # Web application
FrontendType.MOBILE    # Mobile application
FrontendType.API       # API client
```

### AuthProvider
```python
from botspool_shared_utils.enums import AuthProvider

AuthProvider.EMAIL     # Email authentication
AuthProvider.GOOGLE    # Google OAuth2
AuthProvider.GITHUB    # GitHub OAuth2
AuthProvider.MICROSOFT # Microsoft OAuth2
```
