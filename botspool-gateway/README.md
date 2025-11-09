# BotsPool Gateway

Core API Gateway for the BotsPool platform - Authentication, routing, and orchestration for multiple AI graph services.

## 🎯 Overview

The BotsPool Gateway is the central orchestration service that provides:

- **Authentication & Authorization**: JWT-based authentication with RBAC
- **Request Routing**: Intelligent routing to appropriate graph instances
- **Load Balancing**: Multiple strategies (round-robin, least-connections, weighted)
- **Health Monitoring**: Service health checks and metrics
- **Rate Limiting**: Subscription-based usage limits
- **Error Handling**: Comprehensive error handling and resilience patterns

## 🏗️ Architecture

```
Client → Gateway → Graph Pool → AI Agents
         ↓
    PostgreSQL + Redis
```

The gateway integrates with the `botspool-shared-utils` library for common functionality including models, authentication, database utilities, error handling, and more.

## Frontend Clients

The gateway treats frontends as first-class clients:

- Every login includes a `frontend_type` claim (e.g., `telegram`) that drives rate limits and authorization checks.
- The Telegram bot is the only production frontend today, but the same flows apply to future Discord or web adapters—authenticate via `/api/v1/auth/login`, then route chat traffic through the `/api/v1/chat/{graph_type}` endpoints.
- Notification tooling relies on service-to-service API keys and is agnostic to which frontend ultimately delivers the message.

## 🔐 Authentication & Authorization

The Gateway implements a complete authentication and authorization system:

### Features
- **JWT Authentication**: RS256 algorithm with RSA 2048-bit keys
- **User Registration**: Full account creation with database integration
- **Password Security**: bcrypt hashing with strength validation
- **RBAC**: Role-based access control with permission checks
- **Account Protection**: Failed login tracking and automatic lockout
- **Password Reset**: Secure token-based password reset flow
- **Subscription Integration**: Tier-based access control

### User Roles
- **FREE_USER**: Basic access, TODO graph only
- **BASIC_USER**: READ/WRITE permissions, TODO + EMAIL graphs
- **PREMIUM_USER**: + Analytics, TODO + EMAIL + CALENDAR + DOCUMENT graphs
- **ENTERPRISE_USER**: + User management, all graphs
- **ADMIN**: Full administrative access

### Security Features
- RSA 2048-bit key pairs for JWT signing
- Password hashing with bcrypt (12 rounds)
- Password strength requirements (8+ chars, uppercase, lowercase, digit, special)
- Account lockout after 5 failed login attempts
- JTI (JWT ID) for token revocation support
- Token expiration enforcement (1 hour access, 30 days refresh)

## 📦 Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- `botspool-shared-utils` (installed as editable dependency)

### Setup

1. **Clone the repository**:
```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool
git clone <repository-url> botspool-gateway
cd botspool-gateway
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

This will automatically install `botspool-shared-utils` in editable mode from the parent directory.

4. **Configure environment**:
```bash
cp env.example .env
# Edit .env with your configuration
```

5. **Generate JWT keys**:
```bash
# Generate RSA keypair for JWT authentication
python ../scripts/generate-jwt-keys.py

# Copy the output keys into your .env file
# The script will output JWT_PRIVATE_KEY and JWT_PUBLIC_KEY
```

6. **Set up database**:
```bash
# The shared-utils database models will be used
# Migrations will be handled by botspool-shared-utils
```

## 🚀 Usage

### Development Mode

```bash
# Run with auto-reload
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or use the main.py script
cd src
python main.py

# Or use the startup script
./scripts/start.sh
```

### Production Mode

```bash
# Direct execution
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or use the startup script
./scripts/start.sh
```

### Docker Deployment

```bash
# Production deployment
docker-compose up -d

# Development deployment
docker-compose -f docker-compose.dev.yml up -d
```

### Docker

#### Production Deployment

```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f gateway

# Stop services
docker-compose down
```

#### Development Deployment

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f gateway-dev

# Stop development environment
docker-compose -f docker-compose.dev.yml down
```

#### Manual Docker Build

```bash
# Build production image
docker build -t botspool-gateway:latest .

# Build development image
docker build -f Dockerfile.dev -t botspool-gateway:dev .

# Run container
docker run -p 8000:8000 --env-file .env botspool-gateway:latest
```

## 📚 API Documentation

### Interactive API Docs

- **Swagger UI**: http://localhost:8000/docs (development only)
- **ReDoc**: http://localhost:8000/redoc (development only)

### Health Monitoring

- **Basic Health**: http://localhost:8000/health
- **Detailed Status**: http://localhost:8000/health/status
- **Readiness Probe**: http://localhost:8000/health/ready
- **Liveness Probe**: http://localhost:8000/health/live

### Core Endpoints

#### Health Checks
- `GET /health` - Basic health status
- `GET /status` - Detailed system status
- `GET /ready` - Readiness probe
- `GET /live` - Liveness probe

#### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user info
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/password-reset/request` - Request password reset
- `POST /api/v1/auth/password-reset/verify` - Verify reset token
- `POST /api/v1/auth/password-reset/confirm` - Confirm password reset

#### Graph Management
- `GET /api/v1/graphs` - List available graphs
- `GET /api/v1/graphs/{graph_type}/status` - Graph status
- `POST /api/v1/graphs/register` - Register graph instance

#### Chat
- `POST /api/v1/chat/{graph_type}` - Send message to graph
- `POST /api/v1/chat/{graph_type}/stream` - Stream chat with graph
- `GET /api/v1/chat/{graph_type}/status` - Get chat status
- `GET /api/v1/chat/active-requests` - Get active requests

### API Examples

#### Health Check
```bash
# Basic health check
curl http://localhost:8000/health

# Detailed status
curl http://localhost:8000/health/status | jq

# Readiness probe
curl http://localhost:8000/health/ready

# Liveness probe
curl http://localhost:8000/health/live
```

#### Authentication
```bash
# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "johndoe",
    "password": "SecurePass123!",
    "display_name": "John Doe",
    "frontend_type": "web"
  }' | jq

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "password": "SecurePass123!",
    "frontend_type": "web"
  }' | jq

# Response includes access_token and refresh_token
# Use access_token for subsequent requests

# Get current user
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" | jq

# Request password reset
curl -X POST http://localhost:8000/api/v1/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }' | jq

# Verify reset token (from email)
curl -X POST http://localhost:8000/api/v1/auth/password-reset/verify \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "token": "reset_token_from_email"
  }' | jq

# Confirm password reset
curl -X POST http://localhost:8000/api/v1/auth/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "token": "reset_token_from_email",
    "new_password": "NewSecurePass123!"
  }' | jq

# Refresh token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your_refresh_token_here"
  }' | jq
```

#### Graph Management
```bash
# Register a graph instance
curl -X POST http://localhost:8000/api/v1/graphs/register \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instance_id": "todo-001",
    "graph_type": "todo",
    "endpoint": "http://todo-graph:8001",
    "capacity": 100,
    "version": "1.0.0"
  }' | jq

# List all graphs
curl http://localhost:8000/api/v1/graphs \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" | jq

# Get graph status
curl http://localhost:8000/api/v1/graphs/todo/status \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" | jq
```

#### Chat
```bash
# Send message to a graph
curl -X POST http://localhost:8000/api/v1/chat/todo \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a new task: Buy groceries",
    "session_id": "session_123",
    "context": {
      "current_bot": "todo",
      "user_preferences": {
        "language": "en"
      }
    }
  }' | jq

# Stream chat response
curl -X POST http://localhost:8000/api/v1/chat/todo/stream \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are my pending tasks?",
    "session_id": "session_123"
  }' \
  --no-buffer

# Get chat status
curl http://localhost:8000/api/v1/chat/todo/status \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" | jq
```

## 🔧 Configuration

Configuration is managed through environment variables. See `env.example` for all available options.

### Environment Variable Validation

All environment variables are validated at startup:

- **ENVIRONMENT**: Must be one of `development`, `staging`, `production`
- **LOG_LEVEL**: Must be one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **DATABASE_URL**: Must be a valid PostgreSQL connection string
- **REDIS_URL**: Must be a valid Redis connection string
- **JWT_ALGORITHM**: Must be `RS256` (other algorithms not supported)
- **WORKERS**: Must be a positive integer

### Key Configuration Areas

- **Application**: Name, version, environment
- **Server**: Host, port, workers
- **Database**: Connection URL, pool settings
- **Redis**: Connection URL, pool settings
- **JWT**: Algorithm, token expiry, keys
- **CORS**: Allowed origins, methods, headers
- **Rate Limiting**: Requests per minute/hour
- **Graph Services**: Timeout, heartbeat, stale threshold

### `.env` Quick Reference

Copy `env.example` to `.env` and fill in the values below:

| Variable | Purpose | Example |
|----------|---------|---------|
| `ENVIRONMENT` | Runtime mode (`development`, `staging`, `production`) | `development` |
| `DEBUG` | Enables verbose logging | `true` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `DATABASE_URL` | Gateway Postgres connection | `postgresql+asyncpg://postgres:postgres@localhost:5432/botspool_gateway` |
| `REDIS_URL` | Redis connection for rate limiting & registry | `redis://127.0.0.1:6379/0` |
| `JWT_PRIVATE_KEY` | RSA private key (PEM) used to sign tokens | *(leave blank and paste generated key)* |
| `JWT_PUBLIC_KEY` | RSA public key (PEM) used to verify tokens | *(paste matching public key)* |
| `JWT_ALGORITHM` | JWT signing algorithm | `RS256` |
| `JWT_ACCESS_TOKEN_EXPIRY` | Access token lifetime in seconds | `3600` |
| `JWT_REFRESH_TOKEN_EXPIRY` | Refresh token lifetime in seconds | `2592000` |

All sensitive values (keys, secrets) should be left empty in Git-tracked files; generate them locally before running the service.

### Docker Configuration

For Docker deployments, use `env.docker.example`:

```bash
cp env.docker.example .env.docker
# Edit .env.docker with your Docker-specific configuration
# Note: Use Docker service names for database and Redis hosts
```

**Docker-specific considerations**:
- Use `postgres-gateway` instead of `localhost` for database
- Use `redis` instead of `localhost` for Redis
- JWT keys can be mounted as secrets or environment variables
- Set `WORKERS=4` or higher for production load

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_health.py

# Run with verbose output
pytest -v
```

## 🏛️ Project Structure

```
botspool-gateway/
├── src/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── dependencies.py      # Dependency injection
│   ├── auth/                # Authentication module
│   ├── routing/             # Request routing
│   ├── health/              # Health checks
│   ├── graphs/              # Graph management
│   └── api/                 # API endpoints
│       └── v1/
├── tests/                   # Test suite
├── requirements.txt         # Dependencies
├── env.example             # Environment template
├── env.docker.example      # Docker environment template
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose setup
└── README.md              # This file
```

## 🔗 Integration with Shared Utils

This gateway uses `botspool-shared-utils` for:

- **Models**: User, Chat, Graph, Subscription models
- **Authentication**: JWT handling, RBAC, MFA
- **Database**: Async SQLAlchemy utilities
- **Error Handling**: Exception hierarchy, error codes
- **Validation**: Input validation and sanitization
- **Logging**: Structured logging configuration
- **Circuit Breaker**: Resilience patterns
- **Retry Logic**: Exponential backoff strategies

The shared-utils package is installed in editable mode, allowing changes to be immediately reflected in the gateway.

## 📋 Development Workflow

1. Make changes to gateway code
2. If shared-utils changes are needed, modify them in `../botspool-shared-utils`
3. Changes are immediately available (editable install)
4. Run tests to verify changes
5. Commit both repositories if needed

## 🐛 Debugging

### Enable Debug Mode

```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
```

### View Logs

```bash
# Application logs
tail -f logs/gateway.log

# Docker logs
docker-compose logs -f gateway
```

## 📈 Monitoring

The gateway exposes metrics for monitoring:

- Request count and latency
- Error rates by endpoint
- Graph instance health
- Database connection pool stats
- Redis connection stats

Metrics are available at `http://localhost:9090/metrics` (if enabled).

## 🤝 Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Ensure all tests pass
5. Create pull request

## 📄 License

MIT License - See LICENSE file for details

## 🔗 Related Repositories

- [botspool-shared-utils](../botspool-shared-utils) - Shared utilities and models
- [botspool-todo-graph](../botspool-todo-graph) - ToDo graph service
- [botspool-telegram-bot](../botspool-telegram-bot) - Telegram bot frontend

## 📞 Support

For questions or issues:

- GitHub Issues: [Create an issue]
- Documentation: [BotsPool Docs]
- Email: support@botspool.ai

