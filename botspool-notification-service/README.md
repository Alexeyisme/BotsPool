# BotsPool Notification Service

A dedicated microservice for managing proactive notifications from AI agents to users across multiple frontend platforms.

## Overview

The Notification Service enables AI agents to send immediate notifications and schedule reminders to users. It handles scheduling, delivery tracking, rate limiting, and multi-frontend routing.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed.
- Shared infrastructure from the repository root (`docker-compose.infrastructure.yml`) running.
- A `NOTIFICATION_API_KEY` that will also be configured for the Telegram bot and ToDo agent.

### Configure environment

```bash
cp env.sample .env.docker
```

Populate `.env.docker` with:

- `NOTIFICATION_API_KEY`: secret used by bots and agents when calling this service.
- `REDIS_URL`: `redis://botspool-redis:6379/0` when using the standard compose network.
- `TELEGRAM_BOT_URL`: notification ingress endpoint exposed by the Telegram bot (defaults to `http://botspool-telegram:8081` in Docker).
- Optional worker tuning variables (`WORKER_CHECK_INTERVAL_SECONDS`, `MAX_DELIVERY_ATTEMPTS`, `RETRY_DELAY_SECONDS`).

### Run with Docker Compose

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
```

Confirm health:

```bash
curl http://localhost:8090/health
```

The scheduler/worker container starts automatically with the same compose stack.

## Integration with BotsPool

1. **Telegram Bot (`botspool-telegram/.env.docker`)**
   ```
   NOTIFICATION_PORT=8081
   NOTIFICATION_API_KEY=<same key as above>
   ```
   Expose the notification port inside `botspool-telegram/docker-compose.yml` if it is missing:
   ```yaml
   ports:
     - "8080:8080"
     - "8081:8081"
   ```

2. **ToDo Graph (`botspool-todo-graph/.env.docker`)**
   ```
   NOTIFICATION_SERVICE_URL=http://botspool-notification-service:8090
   NOTIFICATION_API_KEY=<same key as above>
   ```

3. **Networking**
   Ensure every service runs on the same Docker network (`botspool-network` / `botspool_default`) so the hostnames above resolve.

## Features

- **Immediate Notifications**: Send notifications to users instantly
- **Scheduled Reminders**: Schedule notifications for future delivery
- **Pluggable Frontends**: Architecture supports multiple clients; Telegram is the only implemented frontend today
- **Rate Limiting**: Prevent notification spam (10/hour per user)
- **Delivery Tracking**: Track delivery status and retry failed notifications
- **Priority-Based Queuing**: Handle urgent notifications with priority
- **Redis-Based Scheduling**: Efficient time-based notification retrieval
- **API Key Authentication**: Secure service-to-service communication

## Architecture

```
┌──────────────┐
│  AI Agents   │ (ToDo, Email, Calendar, etc.)
└──────┬───────┘
       │ (calls notification tools)
       ▼
┌─────────────────────────┐
│  Notification Service   │
│  Port: 8090             │
│  - API endpoints        │
│  - Scheduling logic     │
│  - Rate limiting        │
└──────┬──────────────────┘
       │
┌──────┴──────────────────┐
│  Notification Worker     │ (Separate Container)
│  - Checks every 10s      │
│  - Dispatches due items  │
└──────┬───────────────────┘
       │
       ▼
┌──────────────┐
│ Frontend Bot │ (Telegram today; adapter interface for future clients)
└──────────────┘
```

## API Endpoints

### POST /api/v1/notifications
Send an immediate notification.

**Headers**:
- `X-API-Key`: Notification API key

**Request**:
```json
{
  "user_id": "user-uuid",
  "chat_id": 1153284,
  "frontend": "telegram",
  "message": "Your task is complete!",
  "agent": "todo",
  "priority": "normal",
  "notification_type": "info"
}
```

**Response**:
```json
{
  "notification_id": "immediate",
  "status": "dispatched",
  "timestamp": "2025-11-06T12:00:00Z"
}
```

### POST /api/v1/notifications/schedule
Schedule a notification for future delivery.

**Headers**:
- `X-API-Key`: Notification API key

**Request**:
```json
{
  "user_id": "user-uuid",
  "chat_id": 1153284,
  "frontend": "telegram",
  "message": "Reminder: Review deployment",
  "agent": "todo",
  "notification_type": "reminder",
  "scheduled_for": "2025-11-07T09:00:00Z"
}
```

**Response**:
```json
{
  "notification_id": "abc-123-def-456",
  "status": "pending",
  "scheduled_for": "2025-11-07T09:00:00Z",
  "timestamp": "2025-11-06T12:00:00Z"
}
```

### DELETE /api/v1/notifications/{notification_id}
Cancel a scheduled notification.

**Headers**:
- `X-API-Key`: Notification API key

**Response**:
```json
{
  "status": "cancelled",
  "notification_id": "abc-123-def-456"
}
```

### GET /api/v1/notifications/user/{user_id}
List user's scheduled notifications.

**Headers**:
- `X-API-Key`: Notification API key

**Query Parameters**:
- `status`: Filter by status (optional)

**Response**:
```json
{
  "notifications": [
    {
      "id": "abc-123",
      "message": "Review deployment",
      "scheduled_for": "2025-11-07T09:00:00Z",
      "status": "pending",
      "agent": "todo"
    }
  ],
  "total": 1
}
```

### GET /health
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-06T12:00:00Z",
  "service": "botspool-notification-service",
  "dependencies": {
    "redis": "healthy"
  }
}
```

## Agent Tool Integration

### Available Tools

Agents can use these tools to send notifications:

#### send_notification()
Send an immediate notification to the user.

```python
send_notification(
    message="Your task is complete!",
    priority="normal",  # low, normal, high, urgent
    notification_type="info"  # info, alert, update
)
```

#### schedule_reminder()
Schedule a reminder for future delivery.

```python
schedule_reminder(
    message="Ping me in 5 minutes",
    hours_from_now=0.0833,  # fractional hours supported
    reminder_type="task_due"
)
```

#### cancel_reminder()
Cancel a scheduled reminder.

```python
cancel_reminder(reminder_id="abc-123-def-456")
```

#### list_user_reminders()
List user's scheduled reminders.

```python
list_user_reminders()
```

### Example Usage in Agents

```python
# User: "Remind me tomorrow at 9 AM to review the deployment"
# Agent processes:
1. Creates task in memory
2. Calls schedule_reminder(
     message="Review the deployment",
     hours_from_now=14  # Calculates hours from now
   )
3. Responds: "I've created the task and will remind you in 14 hours!"

# Tomorrow at 9 AM:
# - Worker dispatches notification
# - User receives: "⏰ ToDo Assistant - Reminder: Review the deployment"
```

## Deployment

### Environment Variables

Create `.env.docker` file:

```bash
# Service settings
SERVICE_NAME=botspool-notification-service
HOST=0.0.0.0
PORT=8090
LOG_LEVEL=INFO

# Redis
REDIS_URL=redis://botspool-redis:6379/0

# Frontend endpoints
TELEGRAM_BOT_URL=http://botspool-telegram:8081

# Authentication
NOTIFICATION_API_KEY=your-secure-api-key-here

# Rate limiting
MAX_NOTIFICATIONS_PER_HOUR=10

# Worker configuration
WORKER_CHECK_INTERVAL_SECONDS=10

# Retry configuration
MAX_DELIVERY_ATTEMPTS=3
RETRY_DELAY_SECONDS=60
```

Adjust the interval if you need faster or slower polling.

### Docker Compose

Start both API and worker:

```bash
cd botspool-notification-service
docker compose up -d
```

This starts:
- `botspool-notification-service`: API server on port 8090
- `botspool-notification-worker`: Background worker for scheduled notifications

### Network Configuration

Ensure the service is on the `botspool-network`:

```bash
docker network create botspool-network
```

All BotsPool services must be on this network for service discovery.

## Redis Schema

### Scheduled Notifications

```
# Sorted set for time-based queries
notification:index                          → ZSET (score=timestamp, value=id)

# Individual notification data
notification:scheduled:{timestamp}:{id}     → JSON string

# User's reminders index
notification:user:{user_id}:reminders       → SET of notification IDs

# Delivery tracking
notification:delivery:{id}                  → HASH {status, delivered_at, attempts}

# Rate limiting
notification:ratelimit:{user_id}            → Counter (expires in 3600s)
```

## Configuration for Agent Tools

### ToDo Agent

Add to `.env.docker`:

```bash
NOTIFICATION_SERVICE_URL=http://botspool-notification-service:8090
NOTIFICATION_API_KEY=your-secure-api-key-here
```

### Telegram Bot

Add to `.env.docker`:

```bash
NOTIFICATION_PORT=8081
NOTIFICATION_API_KEY=your-secure-api-key-here
```

Update docker-compose.yml to expose port 8081:

```yaml
ports:
  - "8080:8080"  # Health check
  - "8081:8081"  # Notifications
```

## Testing

### Run Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_scheduler.py -v
```

### Manual Testing

1. **Start services**:
```bash
docker compose up -d
```

2. **Send immediate notification**:
```bash
curl -X POST http://localhost:8090/api/v1/notifications \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret-key-change-in-production" \
  -d '{
    "user_id": "user-123",
    "chat_id": 1153284,
    "frontend": "telegram",
    "message": "Test notification",
    "agent": "todo",
    "priority": "normal",
    "notification_type": "info"
  }'
```

3. **Schedule notification**:
```bash
curl -X POST http://localhost:8090/api/v1/notifications/schedule \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret-key-change-in-production" \
  -d '{
    "user_id": "user-123",
    "chat_id": 1153284,
    "frontend": "telegram",
    "message": "Reminder: Check this",
    "agent": "todo",
    "notification_type": "reminder",
    "scheduled_for": "2025-11-07T09:00:00Z"
  }'
```

4. **List user notifications**:
```bash
curl http://localhost:8090/api/v1/notifications/user/user-123 \
  -H "X-API-Key: dev-secret-key-change-in-production"
```

## Monitoring

### Health Checks

```bash
# Service health
curl http://localhost:8090/health

# Worker logs
docker logs -f botspool-notification-worker
```

### Logs

View service logs:
```bash
docker compose logs -f notification-service
docker compose logs -f notification-worker
```

## Security

### API Key Management

- Use strong, random API keys in production
- Rotate keys regularly
- Store in secure secret management system
- Never commit keys to version control

### Rate Limiting

- Default: 10 notifications per hour per user
- Configurable via `MAX_NOTIFICATIONS_PER_HOUR`
- Prevents notification spam

### Validation

- All inputs validated with Pydantic
- Chat ID validated against user ID
- Message content sanitized

## Troubleshooting

### Worker not processing notifications

**Check**:
1. Worker container is running: `docker ps | grep worker`
2. Redis connection: `docker logs botspool-notification-worker | grep Redis`
3. Scheduled notifications exist: Check Redis with `redis-cli`

### Notifications not delivered

**Check**:
1. Bot is running and healthy: `curl http://localhost:8081/health`
2. API key matches between services
3. Network connectivity: Services on same Docker network
4. Rate limit not exceeded: Check Redis `notification:ratelimit:{user_id}`

### Invalid API key errors

**Check**:
1. `NOTIFICATION_API_KEY` matches in:
   - Notification service `.env.docker`
   - Telegram bot `.env.docker`
   - Agent `.env.docker`

## Future Enhancements

- Additional frontend adapters (e.g., Discord, Web clients)
- Notification preferences per user
- Timezone-aware scheduling
- Notification aggregation (batch similar notifications)
- Smart scheduling (quiet hours)
- Delivery confirmation tracking
- Read receipts
- Notification history API

## License

Part of the BotsPool platform.

