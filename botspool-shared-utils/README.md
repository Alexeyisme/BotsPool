# BotsPool Shared Utils

**Production-ready shared utilities, models, and interfaces for the BotsPool platform.**

[![Tests](https://github.com/Alexeyisme/botspool-shared-utils/actions/workflows/ci.yml/badge.svg)](https://github.com/Alexeyisme/botspool-shared-utils/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This package contains the core data models, utilities, and interfaces used across all BotsPool services. **All components are fully implemented, tested, and production-ready.**

### ✅ **Status: Complete & Tested**
- **Full automated test suite passing** (unit + integration)
- **All APIs implemented and verified**
- **Comprehensive coverage with runtime demos**
- **Production-ready codebase**

### 🚀 **Key Components**
- **Data Models**: Pydantic models for users, chats, subscriptions, graphs, and sessions
- **Authentication**: JWT handling, RBAC, MFA, and OAuth2 integration
- **Database**: Async database utilities with SQLAlchemy, pooling, and migrations
- **Durable Session Service**: Postgres-backed session persistence with Redis caching defaults
- **LangGraph Helpers**: Reusable PostgreSQL checkpointer factory and LangGraph utilities
- **Gateway Integration**: Configurable registration heartbeat for graph services
- **Notification Tooling**: LangGraph-compatible notification client and tool wrappers
- **Encryption**: Production-grade encryption utilities for sensitive data
- **Error Handling**: Comprehensive error classification and handling
- **Logging**: Structured logging configuration for all environments
- **Validation**: Input validation and sanitization utilities
- **PII Protection**: GDPR-compliant anonymization and privacy tools
- **Service Interfaces**: Abstract base classes for services and repositories
- **Utilities**: Circuit breaker, retry manager, Redis integration

## Installation

```bash
# Install from source
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

```python
from botspool_shared_utils.models import User, ChatRequest, ChatResponse
from botspool_shared_utils.models.enums import GraphType, UserRole, SubscriptionTier
from botspool_shared_utils.auth import JWTHandler, PasswordManager, RBACManager
from botspool_shared_utils.encryption import encrypt_data, generate_encryption_key
from botspool_shared_utils.anonymization import PIIAnonymizer
from botspool_shared_utils.validation import validate_email, validate_password

# Create a user
user = User(
    email="user@example.com",
    username="john_doe",
    role=UserRole.USER,
    subscription_tier=SubscriptionTier.FREE
)

# Hash password
password_hash = PasswordManager.hash_password("secure_password")

# Encrypt sensitive data
key = generate_encryption_key()
encrypted_data, iv, auth_tag = encrypt_data("sensitive_info", key)

# Create a chat request
chat_request = ChatRequest(
    message="Hello, world!",
    user_id=user.id,
    graph_type=GraphType.TODO
)

# Anonymize PII data
anonymizer = PIIAnonymizer()
anonymized_text = anonymizer.anonymize("Contact John Doe at john@example.com")

# Validate inputs
is_valid_email = validate_email("user@example.com")
is_strong_password = validate_password("SecurePass123!")
```

## 🧪 **Comprehensive Demo**

Run the comprehensive demo to see all functionality in action:

```bash
python3 comprehensive_demo.py
```

This demonstrates all 70+ APIs and confirms everything is working correctly.

## Key Features

### 🔐 **Security & Authentication**
- JWT token management with RS256 signing
- Role-based access control (RBAC)
- Multi-factor authentication (MFA) support
- OAuth2 integration for external providers
- Password hashing with bcrypt

### 🗄️ **Database & Storage**
- Async SQLAlchemy 2.0 integration
- Connection pooling and health monitoring
- Migration support with Alembic
- Redis integration for caching and sessions

### 🔒 **Encryption & Privacy**
- AES-256-GCM symmetric encryption
- RSA-2048 asymmetric encryption
- PII detection and anonymization
- GDPR/SOC2 compliance utilities

### 📊 **Observability**
- Structured JSON logging
- Performance metrics tracking
- Error classification and handling
- Health monitoring utilities

### ✅ **Input Validation**
- Comprehensive data validation
- XSS and SQL injection protection
- File and URL sanitization
- Schema validation utilities

## Development

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd botspool-shared-utils

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Testing

```bash
# Run all tests (70 tests, 100% passing)
pytest

# Run with coverage
pytest --cov=src

# Run specific test types
pytest -m unit
pytest -m integration

# Run comprehensive demo
python3 comprehensive_demo.py
```

### ✅ **Test Results**
- **Full suite passing** across unit and integration layers
- **Unit tests**: Cover models, errors, notifications, gateway, LangGraph helpers, and utilities
- **Integration tests**: Validate database queries and shared infrastructure flows
- **Comprehensive demo**: Exercises all exposed APIs and service helpers

### Code Quality

```bash
# Format code
black src tests
isort src tests

# Lint code
flake8 src tests
mypy src
```

## Documentation

- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation for all modules
- **[Architecture](docs/ARCHITECTURE.md)** - System design and component architecture
- **[Examples](docs/EXAMPLES.md)** - Usage examples and code samples
- **[Security](docs/SECURITY.md)** - Security best practices and guidelines
- **[Contributing](docs/CONTRIBUTING.md)** - Development guidelines and contribution process
- **[Migration Guide](docs/MIGRATION_GUIDE.md)** - Upgrade and migration instructions
- **[Changelog](docs/CHANGELOG.md)** - Version history and changes

## License

MIT License - see LICENSE file for details.

## Support

For questions, issues, or contributions:
- Check the [documentation](docs/)
- Review the [API reference](docs/API_REFERENCE.md)
- See [contributing guidelines](docs/CONTRIBUTING.md)
- Report issues on the project repository
