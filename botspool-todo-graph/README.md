# BotsPool ToDo Graph Service

A specialized graph service for task management using LangGraph and integrating with the BotsPool Core Gateway.

## 🎯 Overview

The BotsPool ToDo Graph Service provides intelligent task management capabilities through a LangGraph-based AI agent. It integrates seamlessly with the BotsPool Core Gateway for load balancing, authentication, and service discovery.

## 🏗️ Architecture

### Core Components

- **LangGraph Agent**: Intelligent task management using your existing ToDo-Agent implementation
- **FastAPI Service**: RESTful API for task operations
- **Memory Management**: Shared-utils persistence (PostgreSQL) plus LangGraph checkpointer
- **Gateway Integration**: Automatic registration with Core Gateway
- **Health Monitoring**: Comprehensive health checks and metrics

### Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **AI Agent**: LangGraph + LangChain + OpenAI
- **Database**: PostgreSQL 16+ with async SQLAlchemy
- **Caching**: Redis for session management
- **Memory**: LangGraph PostgreSQL checkpointer for persistent agent memory
- **Integration**: BotsPool Core Gateway

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- OpenAI API Key
- BotsPool Core Gateway running

### Installation

1. **Clone and setup**:
```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool/botspool-todo-graph
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Start the service**:
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

### Docker Deployment

The service uses the shared infrastructure defined in `docker-compose.infrastructure.yml`. Make sure to start infrastructure first:

```bash
# Start infrastructure (PostgreSQL for ToDo Graph, Redis)
cd /Users/a.kislitsin/Documents/Development/BotsPool
docker-compose -f docker-compose.infrastructure.yml up -d

# Start ToDo Graph service
cd botspool-todo-graph
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f todo-graph
```

**Note**: The PostgreSQL checkpointer automatically creates required database tables on first startup. No manual schema setup is required.

## 📚 API Documentation

### Interactive API Docs

- **Swagger UI**: http://localhost:8001/docs (development only)
- **ReDoc**: http://localhost:8001/redoc (development only)

### Core Endpoints

#### Chat with ToDo Agent
```http
POST /api/v1/chat
Content-Type: application/json

{
  "message": "Add a task to follow up with the client",
  "user_id": "user_123",
  "session_id": "session_456"
}
```

#### ToDo Management
```http
# Get todos
GET /api/v1/todos?user_id=user_123&status=not_started

# Create todo
POST /api/v1/todos
{
  "task": "Follow up with client",
  "time_to_complete": 30,
  "deadline": "2024-01-15T10:00:00Z",
  "solutions": ["Call client", "Send email"],
  "status": "not_started"
}

# Update todo
PUT /api/v1/todos/{todo_id}
{
  "status": "in_progress"
}

# Delete todo
DELETE /api/v1/todos/{todo_id}
```

#### Health Monitoring
```http
GET /health              # Basic health check
GET /health/status       # Detailed status
GET /health/ready        # Readiness probe
GET /health/live         # Liveness probe
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and adjust the following values:

| Variable | Description | Example / Default |
|----------|-------------|-------------------|
| `ENVIRONMENT` | Runtime mode (`development`, `staging`, `production`) | `development` |
| `DATABASE_URL` | PostgreSQL connection for ToDo memory + LangGraph checkpointer | `postgresql+asyncpg://postgres:postgres@localhost:5433/botspool_todograph` |
| `REDIS_URL` | Redis cache for state and LangGraph tooling | `redis://localhost:6379/0` |
| `GATEWAY_URL` | URL for the BotsPool gateway heartbeat + chat proxy | `http://localhost:8000` |
| `GRAPH_ENDPOINT` | Public endpoint for this graph instance | `http://botspool-todo-graph:8001` |
| `INSTANCE_ID` | Unique identifier reported to the gateway | `todo-local` |
| `OPENAI_API_KEY` | OpenAI key for LangGraph LLM calls | *(leave empty then set locally)* |
| `LANGSMITH_API_KEY` | Optional LangSmith tracing key | *(optional)* |
| `LANGSMITH_TRACING_V2` | Enable LangSmith v2 tracing | `true` |
| `NOTIFICATION_SERVICE_URL` | Base URL for notification API | `http://botspool-notification-service:8090` |
| `NOTIFICATION_API_KEY` | Service-to-service API key for notifications | *(leave empty then set locally)* |

**Note**: The `DATABASE_URL` points to the dedicated ToDo graph Postgres instance (port 5433) to avoid conflicts with the gateway database (port 5432). Keep API keys empty in version control and populate them only in local or deployment secrets managers.

### Graph Configuration

The service automatically registers with the Core Gateway using:
- **Graph Type**: `todo`
- **Graph Name**: `task_maistro`
- **Capacity**: 100 concurrent requests
- **Health Check**: Every 30 seconds

## 🧠 AI Agent Features

### LangGraph Integration

The service uses your existing ToDo-Agent implementation with:

- **Persistent Memory**: PostgreSQL-based checkpointer for conversation history across sessions
- **Thread-Based Isolation**: Each conversation session maintains its own context
- **Intelligent Routing**: Automatic task categorization and prioritization
- **Context Awareness**: Maintains conversation context using LangGraph's checkpoint system

### Task Management

- **Smart Task Creation**: Natural language task extraction
- **Status Tracking**: Not started, in progress, done, archived
- **Deadline Management**: Automatic deadline detection and reminders
- **Solution Suggestions**: AI-generated actionable solutions

## 🔗 Core Gateway Integration

### Automatic Registration

The service automatically registers with the Core Gateway:

```python
# Registration happens on startup
graph_instance = GraphInstance(
    graph_type=GraphType.TODO,
    endpoint="http://localhost:8001",
    status="healthy",
    capacity=100,
    version="1.0.0"
)
```

### Load Balancing

The Core Gateway will:
- Route requests to this service based on load
- Handle failover if the service becomes unavailable
- Monitor health and performance metrics

### Authentication

All requests are authenticated through the Core Gateway using JWT tokens.

## 🏥 Health Monitoring

### Health Checks

- **Database**: PostgreSQL connection and query performance
- **Redis**: Cache connectivity and response time
- **System**: CPU, memory, and disk usage
- **Service**: Overall service health and uptime

### Metrics

- Request processing time
- Memory usage and task counts
- Error rates and success rates
- Gateway registration status

## 🧪 Testing

### Unit Tests

```bash
pytest tests/ -v
```

### Integration Tests

```bash
pytest tests/integration/ -v
```

### Load Testing

```bash
# Test with multiple concurrent requests
python scripts/load_test.py
```

## 📊 Monitoring

### Logs

Structured JSON logs with:
- Request/response tracking
- Error logging and stack traces
- Performance metrics
- Gateway registration events

### Metrics

- Request count and response times
- Memory usage and task statistics
- Database and Redis performance
- AI model usage and costs

## 🔒 Security

### Authentication

- JWT token validation through Core Gateway
- User session management
- Request rate limiting

### Data Protection

- PII detection and anonymization
- Encrypted data storage
- Secure memory management
- Privacy-compliant logging

## 🚀 Deployment

### Production Deployment

1. **Environment Setup**:
```bash
export OPENAI_API_KEY="your_key"
export DATABASE_URL="postgresql://user:pass@host:5432/db"
export REDIS_URL="redis://host:6379/0"
export GATEWAY_URL="https://gateway.botspool.ai"
```

2. **Docker Deployment**:
```bash
docker build -t botspool-todo-graph:latest .
docker run -p 8001:8001 --env-file .env botspool-todo-graph:latest
```

3. **Kubernetes Deployment**:
```yaml
# See k8s/ directory for Kubernetes manifests
kubectl apply -f k8s/
```

### Scaling

- **Horizontal Scaling**: Multiple service instances
- **Load Balancing**: Core Gateway handles distribution
- **Database Scaling**: PostgreSQL read replicas
- **Cache Scaling**: Redis cluster configuration

## 🤝 Contributing

### Development Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
pip install -e ../botspool-shared-utils
```

2. **Run in development mode**:
```bash
python -m uvicorn src.main:app --reload --port 8001
```

3. **Run tests**:
```bash
pytest tests/ -v --cov=src
```

### Code Style

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

## 📞 Support

For questions about the ToDo Graph Service:

- **Documentation**: See `/docs` endpoint
- **Issues**: GitHub Issues
- **Discord**: #botspool-development
- **Email**: support@botspool.ai

---

*This service is part of the BotsPool ecosystem and integrates with the Core Gateway for production deployment.*
