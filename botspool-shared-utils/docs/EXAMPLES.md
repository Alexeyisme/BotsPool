# Usage Examples

This document provides practical examples of how to use the `botspool-shared-utils` package.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Authentication Examples](#authentication-examples)
3. [Database Examples](#database-examples)
4. [Encryption Examples](#encryption-examples)
5. [Error Handling Examples](#error-handling-examples)
6. [Logging Examples](#logging-examples)
7. [PII Anonymization Examples](#pii-anonymization-examples)

## Basic Usage

### Importing the Package

```python
# Import core models
from botspool_shared_utils.models import User, ChatRequest, ChatResponse
from botspool_shared_utils.models.enums import UserRole, GraphType

# Import authentication utilities
from botspool_shared_utils.auth import JWTHandler, PasswordManager

# Import error handling
from botspool_shared_utils.errors import AuthenticationError, ErrorCode

# Import encryption utilities
from botspool_shared_utils.encryption import encrypt_data, decrypt_data

# Import logging
from botspool_shared_utils.logging import setup_logging, get_logger
```

## Authentication Examples

### JWT Token Management

```python
from botspool_shared_utils.auth import JWTHandler
from botspool_shared_utils.models.enums import UserRole

# Initialize JWT handler
jwt_handler = JWTHandler(
    private_key="your-private-key",
    public_key="your-public-key",
    algorithm="RS256"
)

# Create access token
user_id = "user-123"
roles = [UserRole.USER]
token = jwt_handler.create_access_token(
    subject=user_id,
    roles=roles,
    expires_delta=timedelta(hours=1)
)

# Verify token
payload = jwt_handler.decode_token(token)
print(f"User ID: {payload['sub']}")
print(f"Roles: {payload['roles']}")
```

### Password Management

```python
from botspool_shared_utils.auth import PasswordManager

# Hash password
password = "my-secure-password"
hashed_password = PasswordManager.hash_password(password)

# Verify password
is_valid = PasswordManager.verify_password(password, hashed_password)
print(f"Password valid: {is_valid}")
```

## Database Examples

### User Operations

```python
from botspool_shared_utils.database import DatabaseManager
from botspool_shared_utils.models import User
from botspool_shared_utils.models.enums import UserRole, SubscriptionTier

# Initialize database manager
db_manager = DatabaseManager(database_url="postgresql+asyncpg://...")

# Create user
user = User(
    email="test@example.com",
    username="testuser",
    roles=[UserRole.USER],
    current_subscription_tier=SubscriptionTier.FREE
)

# Save user
await db_manager.users.create(user)

# Retrieve user
retrieved_user = await db_manager.users.get_by_id(user.id)
print(f"User: {retrieved_user.email}")
```

## Encryption Examples

### Data Encryption

```python
from botspool_shared_utils.encryption import encrypt_data, decrypt_data, generate_encryption_key

# Generate encryption key
key = generate_encryption_key()

# Encrypt sensitive data
sensitive_data = "This is sensitive information"
encrypted_data, iv, auth_tag = encrypt_data(sensitive_data, key)

# Decrypt data
decrypted_data = decrypt_data(encrypted_data, key, iv, auth_tag)
print(f"Decrypted: {decrypted_data.decode('utf-8')}")
```

### Field-Level Encryption

```python
from botspool_shared_utils.encryption import encrypt_field, decrypt_field

# Encrypt a field
email = "user@example.com"
encrypted_email = encrypt_field(email, key)

# Decrypt the field
decrypted_email = decrypt_field(encrypted_email, key)
print(f"Decrypted email: {decrypted_email.decode('utf-8')}")
```

## Error Handling Examples

### Custom Exceptions

```python
from botspool_shared_utils.errors import AuthenticationError, ErrorCode, ErrorContext

# Create error context
context = ErrorContext(
    user_id="user-123",
    session_id="session-456",
    request_id="req-789"
)

# Raise authentication error
try:
    raise AuthenticationError(
        message="Invalid credentials",
        error_code=ErrorCode.AUTH_INVALID_CREDENTIALS_100,
        details={"field": "password"},
        context=context
    )
except AuthenticationError as e:
    print(f"Error: {e.message}")
    print(f"Code: {e.error_code}")
    print(f"Details: {e.details}")
    print(f"Context: {e.context.to_dict()}")
```

## Logging Examples

### Setup Logging

```python
from botspool_shared_utils.logging import setup_logging, get_logger

# Setup logging for development
setup_logging(
    level="DEBUG",
    environment="development",
    log_file="app.log"
)

# Get logger
logger = get_logger(__name__)

# Log messages
logger.info("Application started")
logger.warning("This is a warning")
logger.error("An error occurred")
```

### Structured Logging

```python
# Log with additional context
logger.info(
    "User authenticated",
    extra={
        "user_id": "user-123",
        "session_id": "session-456",
        "ip_address": "192.168.1.1"
    }
)
```

## PII Anonymization Examples

### Detect PII

```python
from botspool_shared_utils.anonymization import detect_pii, PIIDetector

# Detect PII in text
text = "Contact John Doe at john.doe@example.com or call (555) 123-4567"
detected_pii = detect_pii(text)

for pii in detected_pii:
    print(f"Found {pii['pii_type']}: {pii['value']}")
    print(f"Confidence: {pii['confidence']}")
```

### Anonymize Data

```python
from botspool_shared_utils.anonymization import anonymize_email, anonymize_phone, mask_data

# Anonymize email
email = "john.doe@example.com"
anonymized_email = anonymize_email(email)
print(f"Anonymized email: {anonymized_email}")

# Anonymize phone
phone = "(555) 123-4567"
anonymized_phone = anonymize_phone(phone)
print(f"Anonymized phone: {anonymized_phone}")

# Mask sensitive data
ssn = "123-45-6789"
masked_ssn = mask_data(ssn, preserve_length=True)
print(f"Masked SSN: {masked_ssn}")
```

## Complete Example: User Registration

```python
import asyncio
from botspool_shared_utils.models import User
from botspool_shared_utils.models.enums import UserRole, SubscriptionTier
from botspool_shared_utils.auth import PasswordManager, JWTHandler
from botspool_shared_utils.database import DatabaseManager
from botspool_shared_utils.logging import setup_logging, get_logger
from botspool_shared_utils.errors import ValidationError, ErrorCode

async def register_user(email: str, username: str, password: str):
    """Complete user registration example."""
    
    # Setup logging
    setup_logging(level="INFO", environment="development")
    logger = get_logger(__name__)
    
    try:
        # Initialize services
        db_manager = DatabaseManager(database_url="postgresql+asyncpg://...")
        jwt_handler = JWTHandler(private_key="...", public_key="...")
        
        # Validate input
        if not email or not username or not password:
            raise ValidationError(
                message="Email, username, and password are required",
                error_code=ErrorCode.VALIDATION_FIELD_MISSING_301
            )
        
        # Hash password
        hashed_password = PasswordManager.hash_password(password)
        
        # Create user
        user = User(
            email=email,
            username=username,
            roles=[UserRole.USER],
            current_subscription_tier=SubscriptionTier.FREE
        )
        
        # Save user to database
        await db_manager.users.create(user)
        
        # Create JWT token
        token = jwt_handler.create_access_token(
            subject=user.id,
            roles=user.roles
        )
        
        # Log successful registration
        logger.info(
            "User registered successfully",
            extra={
                "user_id": user.id,
                "email": email,
                "username": username
            }
        )
        
        return {
            "user": user,
            "token": token
        }
        
    except Exception as e:
        logger.error(
            "User registration failed",
            extra={
                "email": email,
                "username": username,
                "error": str(e)
            }
        )
        raise

# Usage
if __name__ == "__main__":
    result = asyncio.run(register_user(
        email="test@example.com",
        username="testuser",
        password="securepassword"
    ))
    print(f"Registration successful: {result['user'].id}")
```

This example demonstrates how to use multiple components of the `botspool-shared-utils` package together in a real-world scenario.
