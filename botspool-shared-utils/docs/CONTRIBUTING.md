# Contributing to BotsPool Shared Utils

Thank you for your interest in contributing to the BotsPool Shared Utils package! This document provides guidelines and information for contributors.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Code Style](#code-style)
4. [Testing](#testing)
5. [Documentation](#documentation)
6. [Pull Request Process](#pull-request-process)
7. [Issue Reporting](#issue-reporting)
8. [Release Process](#release-process)

## Getting Started

### Prerequisites
- Python 3.11 or higher
- Git
- Docker (for testing with databases)
- Poetry or pip (for dependency management)

### Fork and Clone
1. Fork the repository on GitHub
2. Clone your fork locally:
```bash
git clone https://github.com/your-username/botspool-shared-utils.git
cd botspool-shared-utils
```

3. Add the upstream repository:
```bash
git remote add upstream https://github.com/botspool/botspool-shared-utils.git
```

## Development Setup

### 1. Install Dependencies
```bash
# Using pip
pip install -e ".[dev]"

# Using poetry (if available)
poetry install
```

### 2. Install Pre-commit Hooks
```bash
pre-commit install
```

### 3. Set Up Environment Variables
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# Required variables:
# DATABASE_URL=postgresql://user:pass@localhost/botspool
# REDIS_URL=redis://localhost:6379
# JWT_PRIVATE_KEY=your_private_key
# JWT_PUBLIC_KEY=your_public_key
```

### 4. Set Up Database
```bash
# Start PostgreSQL and Redis with Docker
docker-compose up -d postgres redis

# Run database migrations
alembic upgrade head
```

### 5. Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
```

## Code Style

### Python Style Guide
We follow PEP 8 with some modifications:

- **Line Length**: 88 characters (Black default)
- **Import Order**: isort configuration
- **Type Hints**: Required for all public functions
- **Docstrings**: Google style docstrings

### Code Formatting
```bash
# Format code with Black
black src tests

# Sort imports with isort
isort src tests

# Check code style
flake8 src tests

# Type checking
mypy src
```

### Pre-commit Hooks
Pre-commit hooks automatically format and check your code:

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### Code Structure
```
src/
├── models/           # Pydantic data models
├── errors/          # Error handling and exceptions
├── database/        # Database utilities and ORM
├── auth/           # Authentication and authorization
├── logging/        # Logging configuration
├── encryption/     # Data encryption utilities
├── anonymization/  # PII anonymization
├── validation/     # Input validation
└── interfaces/     # Service interfaces
```

## Testing

### Test Structure
```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for component interactions
├── fixtures/       # Test fixtures and data
└── conftest.py     # Test configuration
```

### Writing Tests

#### Unit Tests
Test individual components in isolation:

```python
import pytest
from botspool_shared_utils.models import User, UserRole
from botspool_shared_utils.enums import SubscriptionTier

def test_user_creation():
    """Test user creation with valid data."""
    user = User(
        auth=UserAuth(email="test@example.com"),
        profile=UserProfile(username="testuser"),
        role=UserRole.FREE_USER,
        subscription_tier=SubscriptionTier.FREE
    )
    
    assert user.auth.email == "test@example.com"
    assert user.profile.username == "testuser"
    assert user.role == UserRole.FREE_USER
```

#### Integration Tests
Test component interactions:

```python
import pytest
from botspool_shared_utils.database import get_database_manager
from botspool_shared_utils.database.queries import UserQueries

@pytest.mark.asyncio
async def test_user_database_operations():
    """Test user database operations."""
    db_manager = get_database_manager()
    
    async with db_manager.get_session_context() as session:
        user_queries = UserQueries(session)
        
        # Create user
        user = await user_queries.create_user({
            "email": "test@example.com",
            "username": "testuser"
        })
        
        # Retrieve user
        retrieved_user = await user_queries.get_user_by_email("test@example.com")
        
        assert retrieved_user is not None
        assert retrieved_user.auth.email == "test@example.com"
```

#### Test Fixtures
Create reusable test data:

```python
# tests/fixtures/user_fixtures.py
import pytest
from botspool_shared_utils.models import User, UserAuth, UserProfile
from botspool_shared_utils.enums import UserRole, SubscriptionTier

@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        auth=UserAuth(
            email="test@example.com",
            password_hash="hashed_password"
        ),
        profile=UserProfile(
            username="testuser",
            first_name="Test",
            last_name="User"
        ),
        role=UserRole.FREE_USER,
        subscription_tier=SubscriptionTier.FREE
    )

@pytest.fixture
def premium_user():
    """Create a premium user for testing."""
    return User(
        auth=UserAuth(email="premium@example.com"),
        profile=UserProfile(username="premiumuser"),
        role=UserRole.PREMIUM_USER,
        subscription_tier=SubscriptionTier.PREMIUM
    )
```

### Test Markers
Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_user_model():
    """Unit test for user model."""
    pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_operations():
    """Integration test for database operations."""
    pass

@pytest.mark.slow
def test_performance():
    """Slow performance test."""
    pass
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test function
pytest tests/unit/test_models.py::test_user_creation
```

## Documentation

### Code Documentation
- **Docstrings**: Use Google style docstrings for all public functions and classes
- **Type Hints**: Include type hints for all function parameters and return values
- **Comments**: Add comments for complex logic and business rules

```python
def create_user(
    email: str,
    username: str,
    password: str,
    **kwargs: Any
) -> User:
    """Create a new user with the provided information.
    
    Args:
        email: User's email address
        username: Unique username
        password: Plain text password (will be hashed)
        **kwargs: Additional user attributes
        
    Returns:
        Created User instance
        
    Raises:
        ValidationError: If input validation fails
        DuplicateUserError: If username or email already exists
        
    Example:
        >>> user = create_user(
        ...     email="user@example.com",
        ...     username="johndoe",
        ...     password="SecurePassword123!"
        ... )
        >>> print(user.profile.username)
        johndoe
    """
    pass
```

### API Documentation
- **README.md**: Project overview and quick start
- **ARCHITECTURE.md**: Detailed architecture documentation
- **API_REFERENCE.md**: Complete API reference
- **MIGRATION_GUIDE.md**: Version migration guide

### Documentation Updates
When adding new features:
1. Update docstrings for new functions/classes
2. Add examples to API_REFERENCE.md
3. Update ARCHITECTURE.md if architecture changes
4. Update CHANGELOG.md with new features

## Pull Request Process

### 1. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes
- Write code following the style guide
- Add tests for new functionality
- Update documentation
- Ensure all tests pass

### 3. Commit Changes
```bash
git add .
git commit -m "feat: add new feature description"
```

Use conventional commit messages:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions/changes
- `refactor:` for code refactoring
- `perf:` for performance improvements

### 4. Push and Create PR
```bash
git push origin feature/your-feature-name
```

Create a pull request on GitHub with:
- Clear title and description
- Reference related issues
- Include test results
- Add screenshots if applicable

### 5. PR Review Process
- Automated checks must pass (tests, linting, type checking)
- Code review by maintainers
- Address feedback and make requested changes
- Squash commits if requested

### 6. Merge
- PR is merged by maintainers
- Delete feature branch after merge

## Issue Reporting

### Bug Reports
When reporting bugs, include:
- **Description**: Clear description of the bug
- **Steps to Reproduce**: Detailed steps to reproduce
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: Python version, OS, package version
- **Code Sample**: Minimal code to reproduce the issue

### Feature Requests
When requesting features, include:
- **Description**: Clear description of the feature
- **Use Case**: Why this feature is needed
- **Proposed Solution**: How you think it should work
- **Alternatives**: Other solutions you've considered

### Issue Templates
Use the provided issue templates:
- Bug report template
- Feature request template
- Documentation improvement template

## Release Process

### Version Numbering
We use [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Steps
1. **Update Version**: Update version in `pyproject.toml`
2. **Update Changelog**: Add new version to `CHANGELOG.md`
3. **Create Release**: Create GitHub release with tag
4. **Publish Package**: Publish to PyPI
5. **Update Documentation**: Update documentation if needed

### Release Checklist
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Changelog is updated
- [ ] Version is bumped
- [ ] Release notes are written
- [ ] Package is published to PyPI

## Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inclusive environment for all contributors.

### Expected Behavior
- Be respectful and inclusive
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy towards other community members

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or insulting comments
- Personal attacks or political discussions
- Public or private harassment

### Enforcement
Violations of the code of conduct will be addressed by project maintainers.

## Getting Help

### Communication Channels
- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Email**: For security issues (security@botspool.ai)

### Resources
- **Documentation**: Check the docs/ directory
- **Examples**: Look at the examples/ directory
- **Tests**: Check tests/ for usage examples
- **API Reference**: See API_REFERENCE.md

### Mentorship
New contributors can request mentorship by:
1. Opening an issue with the "help wanted" label
2. Mentioning that you're new to the project
3. Asking specific questions about where to start

## Recognition

### Contributors
All contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

### Types of Contributions
We welcome various types of contributions:
- **Code**: Bug fixes, new features, improvements
- **Documentation**: Improvements, examples, tutorials
- **Testing**: Test cases, test improvements
- **Design**: UI/UX improvements, architecture suggestions
- **Community**: Helping other users, answering questions

Thank you for contributing to BotsPool Shared Utils! 🚀
