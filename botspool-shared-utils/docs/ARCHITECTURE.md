# BotsPool Shared Utils Architecture

## Table of Contents
1. [Overview](#1-overview)
2. [Component Architecture](#2-component-architecture)
3. [Data Models](#3-data-models)
4. [Error Handling](#4-error-handling)
5. [Database Layer](#5-database-layer)
6. [Authentication & Authorization](#6-authentication--authorization)
7. [Security](#7-security)
8. [Performance](#8-performance)
9. [Dependencies](#9-dependencies)
10. [Usage Examples](#10-usage-examples)
11. [Development Guidelines](#11-development-guidelines)

## 1. Overview

### Purpose
The `botspool-shared-utils` package provides the foundational components used across all BotsPool services. It contains shared data models, utilities, and interfaces that ensure consistency and reduce code duplication across the platform.

### Key Principles
- **Type Safety**: Pydantic models with comprehensive validation
- **Consistency**: Standardized interfaces and data structures
- **Security**: Built-in security features and best practices
- **Performance**: Optimized for high-throughput scenarios
- **Maintainability**: Clear separation of concerns and modular design

### Core Responsibilities
- **Data Models**: Pydantic models for all platform entities
- **Error Handling**: Comprehensive error classification and handling
- **Database Operations**: Async database utilities, ORM models, and migrations
- **Authentication**: JWT, RBAC, MFA, and OAuth2 support
- **Security**: Password management, encryption, and session handling
- **Durable Sessions**: Postgres-backed session storage with Redis caching defaults
- **LangGraph Support**: Shared checkpointer factory and graph utilities
- **Gateway Integration**: Registration heartbeat and lifecycle helpers for graph services
- **Notification Tooling**: HTTP client and LangChain-compatible tool wrappers for outbound messaging

## 2. Component Architecture

### High-Level Structure
```
botspool-shared-utils/
├── src/
│   ├── models/           # Data models and schemas
│   ├── errors/           # Error handling and classification
│   ├── database/         # Database utilities and ORM
│   ├── auth/             # Authentication and authorization
│   ├── logging/          # Logging configuration
│   ├── encryption/       # Data encryption utilities
│   ├── anonymization/    # PII anonymization
│   ├── validation/       # Input validation
│   ├── interfaces/       # Service interfaces
│   ├── langgraph/        # LangGraph helpers (e.g., Postgres checkpointer factory)
│   ├── gateway/          # Gateway registration utilities
│   ├── notifications/    # Notification client and LangChain tool wrappers
│   ├── sessions/         # Durable session service with cache integration
│   └── circuit_breaker.py retry.py redis_utils.py  # Cross-cutting utilities
├── tests/              # Test suite
├── docs/              # Documentation
└── requirements.txt   # Dependencies
```

### Component Dependencies
```
┌─────────────────────────────────────────────────────────────┐
│                    External Services                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ PostgreSQL  │  │    Redis    │  │   OAuth2    │        │
│  │  Database   │  │    Cache    │  │  Providers  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                botspool-shared-utils                        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Models    │  │   Errors    │  │  Database   │        │
│  │   Layer     │  │   Layer     │  │   Layer     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │    Auth     │  │  Security   │  │  Utilities  │        │
│  │   Layer     │  │   Layer     │  │   Layer     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  BotsPool Services                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Gateway   │  │   Graphs    │  │  Frontends  │        │
│  │  Services   │  │  Services   │  │  Services   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## 3. Data Models

### Model Hierarchy
```
BaseModel (Pydantic)
├── TimestampMixin
├── MetadataMixin
├── IdentifiableMixin
├── VersionedMixin
└── SoftDeleteMixin
    └── BaseEntity
        └── BaseAuditableEntity
```

### Core Entity Models

#### User Models
```python
User (BaseEntity)
├── UserAuth (authentication info)
├── UserProfile (profile data)
├── UserPreferences (settings)
└── UserSession (active sessions)
```

#### Chat Models
```python
ChatSession (BaseEntity)
├── ChatMessage (individual messages)
├── ChatRequest (incoming requests)
├── ChatResponse (outgoing responses)
└── ChatContext (session context)
```

#### Subscription Models
```python
Subscription (BaseEntity)
├── SubscriptionPlan (plan definitions)
├── UsageLimit (usage constraints)
└── UsageTracking (current usage)
```

#### Graph Models
```python
Graph (BaseEntity)
├── GraphInstance (running instances)
├── GraphHealth (health metrics)
└── GraphConfig (configuration)
```

### Enum Types
- **SubscriptionTier**: FREE, BASIC, PREMIUM, ENTERPRISE
- **GraphType**: TODO, EMAIL, CALENDAR, DOCUMENT, CODE, RESEARCH
- **UserRole**: FREE_USER, BASIC_USER, PREMIUM_USER, ENTERPRISE_USER, ADMIN, DEVELOPER
- **Permission**: READ_GRAPHS, WRITE_GRAPHS, ADMIN_GRAPHS, etc.
- **ChatStatus**: ACTIVE, PAUSED, ENDED, ERROR
- **GraphStatus**: HEALTHY, DEGRADED, UNHEALTHY, MAINTENANCE, OFFLINE
- **FrontendType**: TELEGRAM, DISCORD, WEB, MOBILE, API
- **AuthProvider**: EMAIL, GOOGLE, GITHUB, MICROSOFT

## 4. Error Handling

### Error Classification System
```
BotsPoolError (Base Exception)
├── AuthenticationError
│   ├── TokenExpiredError
│   ├── InvalidTokenError
│   └── InsufficientPermissionsError
├── ValidationError
├── GraphError
│   ├── GraphUnavailableError
│   └── GraphTimeoutError
├── DatabaseError
│   ├── DatabaseConnectionError
│   └── DatabaseQueryError
├── ExternalServiceError
│   ├── OpenAIServiceError
│   ├── RedisServiceError
│   └── PostgresServiceError
├── RateLimitError
│   └── RateLimitExceededError
├── SubscriptionError
│   └── SubscriptionLimitExceededError
└── ConfigurationError
    ├── InvalidConfigurationError
    └── MissingConfigurationError
```

### Error Code Format
- **Pattern**: `SERVICE_ACTION_NUMBER`
- **Examples**: 
  - `AUTH_TOKEN_EXPIRED_001`
  - `GRAPH_SERVICE_UNAVAILABLE_001`
  - `DATABASE_CONNECTION_FAILED_001`

### Error Categories
- **Authentication**: User authentication failures
- **Authorization**: Permission and access control issues
- **Validation**: Input validation errors
- **Graph**: AI graph service issues
- **Database**: Database operation failures
- **External Service**: Third-party service failures
- **Rate Limit**: Rate limiting violations
- **Subscription**: Subscription and billing issues
- **Configuration**: Configuration and setup errors
- **Internal**: Internal system errors

### Error Context
```python
ErrorContext {
    request_id: str
    user_id: UUID
    session_id: str
    conversation_id: str
    graph_type: str
    frontend_type: str
    ip_address: str
    user_agent: str
    endpoint: str
    method: str
    timestamp: datetime
    additional_data: Dict[str, Any]
}
```

## 5. Database Layer

### Connection Management
```python
DatabaseManager {
    - Connection pooling with configurable limits
    - Health checks and automatic reconnection
    - Transaction management with context managers
    - Query performance monitoring
    - Connection pool monitoring
}
```

### ORM Models
- **UserModel**: Main user entity with relationships
- **UserAuthModel**: Authentication information
- **UserProfileModel**: User profile data
- **UserPreferencesModel**: User settings
- **UserSessionModel**: Active user sessions
- **ChatSessionModel**: Chat conversation sessions
- **ChatMessageModel**: Individual chat messages
- **SubscriptionModel**: User subscriptions
- **SubscriptionPlanModel**: Subscription plan definitions
- **UsageTrackingModel**: Usage tracking and limits
- **GraphModel**: AI graph definitions
- **GraphInstanceModel**: Running graph instances
- **GraphHealthModel**: Graph health metrics

### Query Utilities
```python
QueryBuilder (Base)
├── UserQueries
├── ChatQueries
├── SubscriptionQueries
├── GraphQueries
└── SessionQueries
```

### Migration Support
- **Alembic Integration**: Database schema versioning
- **Migration Manager**: Automated migration handling
- **Rollback Support**: Safe rollback capabilities
- **Migration History**: Track migration status

### Performance Monitoring
- **Query Performance**: Track query execution times
- **Connection Pool**: Monitor pool utilization
- **Health Checks**: Database health monitoring
- **Metrics Collection**: Performance metrics

## 6. Authentication & Authorization

### JWT Management
```python
JWTHandler {
    - RS256 algorithm for signing
    - Access and refresh token generation
    - Token validation and verification
    - Token refresh mechanism
    - Token revocation support
}
```

### JWT Token Structure
```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_id",
    "iss": "botspool.ai",
    "aud": "botspool-api",
    "iat": 1640995200,
    "exp": 1641081600,
    "type": "access|refresh",
    "role": "premium_user",
    "permissions": ["read_graphs", "write_graphs"],
    "jti": "unique_token_id"
  }
}
```

### Role-Based Access Control (RBAC)
```python
RBACManager {
    - Role definitions with permissions
    - Permission inheritance hierarchy
    - Graph access control
    - Rate limit management
    - Feature access control
}
```

### Password Security
```python
PasswordManager {
    - Bcrypt hashing with configurable rounds
    - Password strength validation
    - Secure password generation
    - Password reset token management
}
```

### Multi-Factor Authentication (MFA)
```python
MFAHandler {
    - TOTP secret generation
    - QR code generation for setup
    - Token verification
    - Backup code generation
    - MFA status checking
}
```

### OAuth2 Integration
```python
OAuthManager {
    - Google OAuth2 provider
    - GitHub OAuth2 provider
    - Extensible provider system
    - User info normalization
}
```

### Session Management
```python
SessionService {
    - Postgres source of truth for durable sessions
    - Redis cache (write-through, enabled by default)
    - Frontend/chat scoped lookups (Telegram, Discord, etc.)
    - Session refresh, expiry, and purge operations
    - User-centric queries for active sessions
}
```

## 7. Security

### Data Protection
- **Encryption at Rest**: Database and file encryption
- **Encryption in Transit**: TLS for all communications
- **Password Hashing**: Bcrypt with salt
- **Token Security**: JWT with RS256 signing
- **Session Security**: Secure session management

### Input Validation
- **Pydantic Models**: Automatic validation and sanitization
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Output encoding
- **CSRF Protection**: Token-based protection

### Access Control
- **JWT Authentication**: Stateless authentication
- **RBAC Authorization**: Role-based permissions
- **Graph Access Control**: Subscription-based access
- **Rate Limiting**: Per-user and per-endpoint limits

### Privacy
- **PII Anonymization**: Data anonymization utilities
- **Data Minimization**: Collect only necessary data
- **Audit Logging**: Comprehensive audit trails
- **GDPR Compliance**: Data protection compliance

## 8. Performance

### Database Performance
- **Connection Pooling**: Efficient connection management
- **Query Optimization**: Optimized query patterns
- **Indexing Strategy**: Proper database indexing
- **Caching**: Redis-based caching
- **Connection Monitoring**: Pool health monitoring

### Memory Management
- **Efficient Models**: Optimized Pydantic models
- **Lazy Loading**: On-demand data loading
- **Memory Monitoring**: Memory usage tracking
- **Garbage Collection**: Proper resource cleanup

### Async Operations
- **Async/Await**: Non-blocking operations
- **Concurrent Processing**: Parallel operation support
- **Connection Pooling**: Async connection management
- **Background Tasks**: Async background processing

## 9. Dependencies

### Core Dependencies
```
pydantic>=2.0.0,<3.0.0          # Data validation and serialization
email-validator>=2.0.0,<3.0.0   # Email validation
sqlalchemy>=2.0.0,<3.0.0        # ORM and database toolkit
asyncpg>=0.28.0,<1.0.0          # Async PostgreSQL driver
alembic>=1.12.0,<2.0.0          # Database migration tool
redis>=4.5.0,<5.0.0             # Redis client
aioredis>=2.0.0,<3.0.0          # Async Redis client
python-jose[cryptography]>=3.3.0 # JWT handling
passlib[bcrypt]>=1.7.4          # Password hashing
cryptography>=41.0.0            # Cryptographic operations
python-dateutil>=2.8.0          # Date/time utilities
pytz>=2023.3                    # Timezone handling
```

### Development Dependencies
```
pytest>=7.4.0                   # Testing framework
pytest-asyncio>=0.21.0          # Async testing support
pytest-cov>=4.1.0               # Coverage reporting
black>=23.7.0                   # Code formatting
isort>=5.12.0                   # Import sorting
flake8>=6.0.0                   # Linting
mypy>=1.5.0                     # Type checking
pre-commit>=3.3.0               # Pre-commit hooks
```

## 10. Usage Examples

### Basic Model Usage
```python
from botspool_shared_utils.models import User, UserCreate, SubscriptionTier
from botspool_shared_utils.enums import UserRole, GraphType

# Create a user
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
    role=UserRole.FREE_USER,
    subscription_tier=SubscriptionTier.FREE
)

# Validate user creation
user_create = UserCreate(
    email="user@example.com",
    username="john_doe",
    password="SecurePassword123!",
    first_name="John",
    last_name="Doe"
)
```

### Error Handling
```python
from botspool_shared_utils.errors import (
    AuthenticationError, 
    TokenExpiredError,
    ErrorContext,
    handle_error
)

try:
    # Some operation that might fail
    result = await some_operation()
except TokenExpiredError as e:
    # Add context to error
    context = ErrorContext(
        request_id="req_123",
        user_id="user_456",
        frontend_type="telegram"
    )
    
    # Handle error with context
    error_response = handle_error(e, context)
    return error_response
```

### Database Operations
```python
from botspool_shared_utils.database import (
    get_database_manager,
    UserQueries,
    ChatQueries
)

# Get database manager
db_manager = get_database_manager()

# Use query utilities
async with db_manager.get_session_context() as session:
    user_queries = UserQueries(session)
    chat_queries = ChatQueries(session)
    
    # Get user by email
    user = await user_queries.get_user_by_email("user@example.com")
    
    # Get user's chat sessions
    sessions = await chat_queries.get_chat_sessions_by_user(user.id)
```

### Authentication
```python
from botspool_shared_utils.auth import (
    get_auth_service,
    authenticate_user,
    FrontendType
)

# Authenticate user
auth_service = get_auth_service()
result = await auth_service.authenticate_user(
    email="user@example.com",
    password="password",
    frontend_type=FrontendType.TELEGRAM
)

# Check permissions
from botspool_shared_utils.auth import check_permission, Permission
from botspool_shared_utils.enums import UserRole

has_permission = check_permission(
    UserRole.PREMIUM_USER, 
    Permission.READ_GRAPHS
)
```

## 11. Development Guidelines

### Code Style
- **PEP 8 Compliance**: Follow Python style guidelines
- **Type Hints**: Use type hints for all functions and methods
- **Docstrings**: Document all public functions and classes
- **Error Handling**: Use specific exception types
- **Async/Await**: Use async operations for I/O

### Testing
- **Unit Tests**: Test individual components
- **Integration Tests**: Test component interactions
- **Coverage**: Maintain high test coverage
- **Mocking**: Mock external dependencies
- **Fixtures**: Use pytest fixtures for test data

### Documentation
- **API Documentation**: Document all public APIs
- **Examples**: Provide usage examples
- **Changelog**: Maintain version changelog
- **Migration Guide**: Document breaking changes

### Security
- **Input Validation**: Validate all inputs
- **Error Messages**: Don't expose sensitive information
- **Logging**: Log security-relevant events
- **Dependencies**: Keep dependencies updated
- **Secrets**: Never commit secrets to version control

### Performance
- **Profiling**: Profile performance-critical code
- **Caching**: Use caching where appropriate
- **Database**: Optimize database queries
- **Memory**: Monitor memory usage
- **Async**: Use async operations for I/O

### Maintenance
- **Versioning**: Use semantic versioning
- **Deprecation**: Properly deprecate old APIs
- **Migration**: Provide migration paths
- **Monitoring**: Monitor usage and performance
- **Updates**: Keep dependencies updated
