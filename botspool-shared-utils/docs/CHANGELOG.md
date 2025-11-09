# Changelog

All notable changes to the `botspool-shared-utils` package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial implementation of core data models
- Comprehensive error handling system
- Database utilities and ORM models
- Authentication and authorization system
- JWT token management with RS256
- RBAC (Role-Based Access Control) system
- Password security with bcrypt
- Multi-Factor Authentication (MFA) support
- OAuth2 integration (Google, GitHub)
- Durable session service (Postgres persistence with Redis caching)
- Database connection pooling
- Query utilities and performance monitoring
- Migration support with Alembic
- Comprehensive test suite
- Documentation and examples

### Security
- JWT tokens with RS256 algorithm
- Password hashing with bcrypt
- Input validation with Pydantic
- SQL injection prevention
- XSS protection
- CSRF protection
- Rate limiting support
- Session security
- MFA support with TOTP

### Performance
- Async database operations
- Connection pooling
- Query performance monitoring
- Memory optimization
- Efficient data models

## [0.1.0] - 2024-01-XX

### Added
- Initial release
- Core data models (User, Chat, Subscription, Graph)
- Error handling system with 80+ error codes
- Database layer with SQLAlchemy ORM
- Authentication system with JWT, RBAC, MFA, OAuth2
- Session management with Redis
- Comprehensive documentation
- Test suite with unit and integration tests
