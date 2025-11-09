# Notification Service Deployment Guide

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- BotsPool network created: `docker network create botspool-network`
- Redis running on `botspool-network`
- Telegram bot running with notification endpoint

### 2. Environment Configuration

Create `.env.docker` file (copy from `env.sample`):

```bash
cp env.sample .env.docker
```

**Required configuration**:
- `NOTIFICATION_API_KEY`: Must match across all services (bot, agent, notification)
- `REDIS_URL`: Redis connection string
- `TELEGRAM_BOT_URL`: Bot notification endpoint URL
- `WORKER_CHECK_INTERVAL_SECONDS`: Poll interval for scheduled dispatcher (default `10` seconds)

### 3. Deploy

```bash
# Build and start
docker compose up -d

# Verify services
docker compose ps

# Check logs
docker compose logs -f
```

### 4. Verify Deployment

```bash
# Health check
curl http://localhost:8090/health

# Should return:
{
  "status": "healthy",
  "dependencies": {
    "redis": "healthy"
  }
}
```

## Integration with Existing Services

### Step 1: Update Telegram Bot

Add to `botspool-telegram/.env.docker`:
```bash
NOTIFICATION_PORT=8081
NOTIFICATION_API_KEY=your-secure-api-key-here
CREDENTIAL_ENCRYPTION_KEY=your-32-byte-fernet-key
```

Add to `botspool-telegram/docker-compose.yml`:
```yaml
ports:
  - "8080:8080"
  - "8081:8081"  # ADD THIS
```

Rebuild bot:
```bash
cd botspool-telegram
docker compose up -d --build
```

### Step 2: Update ToDo Agent

Add to `botspool-todo-graph/.env.docker`:
```bash
NOTIFICATION_SERVICE_URL=http://botspool-notification-service:8090
NOTIFICATION_API_KEY=your-secure-api-key-here
```

Rebuild agent:
```bash
cd botspool-todo-graph
docker compose up -d --build
```

### Step 3: Start Notification Service

```bash
cd botspool-notification-service
docker compose up -d
```

### Step 4: Verify Integration

Test the full flow:

```bash
# 1. Get JWT token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"testuser","password":"testpass123","frontend_type":"web"}' | \
  jq -r '.access_token')

# 2. Send message asking for notification
curl -X POST "http://localhost:8000/api/v1/chat/todo?user_id=user-123" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Send me a test notification","session_id":"1153284_todo"}' | jq .

# 3. Check if agent called notification tool (check agent logs)
docker logs botspool-todo-graph | grep notification
```

## Service Architecture

### Running Services

After deployment, you'll have:

1. **notification-service** (Port 8090): REST API
2. **notification-worker** (No ports): Background processor
3. **telegram-bot** (Ports 8080, 8081): Bot + notification endpoint

### Service Communication

```
Agent → Notification Service (8090) → Telegram Bot (8081) → Telegram API
                ↓
        Redis (Scheduling)
                ↓
        Worker (Background)
```

## Configuration Matrix

### API Keys

**IMPORTANT**: The same API key must be used across all services.

| Service | Environment Variable | Used For |
|---------|---------------------|----------|
| Notification Service | `NOTIFICATION_API_KEY` | Validate incoming requests |
| Telegram Bot | `NOTIFICATION_API_KEY` | Validate notification requests |
| ToDo Agent | `NOTIFICATION_API_KEY` | Authenticate with notification service |
| Other Agents | `NOTIFICATION_API_KEY` | Authenticate with notification service |

### Service URLs

| From | To | Environment Variable | Value |
|------|----|--------------------|-------|
| Agent | Notification Service | `NOTIFICATION_SERVICE_URL` | `http://botspool-notification-service:8090` |
| Notification Service | Telegram Bot | `TELEGRAM_BOT_URL` | `http://botspool-telegram:8081` |

## Deployment Checklist

### Pre-Deployment

- [ ] Docker network created: `botspool-network`
- [ ] Redis running and accessible
- [ ] Telegram bot updated with notification endpoint
- [ ] Environment variables configured
- [ ] API key generated and set across all services

### Deployment

- [ ] Notification service built: `docker compose build`
- [ ] Services started: `docker compose up -d`
- [ ] Health checks passing: `curl http://localhost:8090/health`
- [ ] Worker running: `docker ps | grep worker`

### Post-Deployment

- [ ] Test immediate notification
- [ ] Test scheduled notification
- [ ] Verify worker processes due notifications (should poll every 10 seconds)
- [ ] Check logs for errors
- [ ] Monitor Redis for scheduled items

## Testing

### Unit Tests

```bash
cd botspool-notification-service
pip install -r requirements-dev.txt
pytest
```

### Integration Test

```bash
# Test immediate notification
curl -X POST http://localhost:8090/api/v1/notifications \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret-key-change-in-production" \
  -d '{
    "user_id": "user-123",
    "chat_id": 1153284,
    "frontend": "telegram",
    "message": "Test notification",
    "agent": "todo"
  }'

# Check Telegram for message
```

### End-to-End Test

1. Talk to bot in Telegram: "Remind me in 1 minute to check this"
2. Agent should call `schedule_reminder` tool
3. Check notification service logs: `docker logs botspool-notification-service`
4. Check Redis: `docker exec botspool-redis redis-cli ZRANGE notification:index 0 -1`
5. Wait 1 minute
6. Check worker logs: `docker logs botspool-notification-worker`
7. Verify notification received in Telegram

## Monitoring

### Service Logs

```bash
# API service
docker logs -f botspool-notification-service

# Worker
docker logs -f botspool-notification-worker

# All notification services
docker compose logs -f
```

### Redis Inspection

```bash
# Connect to Redis
docker exec -it botspool-redis redis-cli

# View scheduled notifications
ZRANGE notification:index 0 -1 WITHSCORES

# View specific notification
GET notification:scheduled:{timestamp}:{id}

# View user's reminders
SMEMBERS notification:user:{user_id}:reminders

# Check rate limits
GET notification:ratelimit:{user_id}
```

### Health Monitoring

```bash
# Service health
watch -n 5 'curl -s http://localhost:8090/health | jq .'

# Worker status
docker stats botspool-notification-worker
```

## Scaling

### Horizontal Scaling

**API Service**:
- Can scale to multiple instances
- Stateless (uses Redis for all state)
- Load balance with nginx or k8s ingress

**Worker**:
- Run single instance (prevents duplicate processing)
- Or use distributed locking for multiple workers

### Performance Tuning

**Worker Check Interval**:
```bash
# Default (recommended)
WORKER_CHECK_INTERVAL_SECONDS=10

# For lower CPU usage (slower notifications)
WORKER_CHECK_INTERVAL_SECONDS=30
```

**Rate Limiting**:
```bash
# Adjust per use case
MAX_NOTIFICATIONS_PER_HOUR=20
```

## Troubleshooting

### Notifications not being sent

**Symptoms**: Scheduled notifications not delivered

**Check**:
1. Worker is running: `docker ps | grep worker`
2. Worker logs: `docker logs botspool-notification-worker`
3. Redis has notifications: `redis-cli ZRANGE notification:index 0 -1`
4. Current time: `date -u` (must be >= scheduled time)

**Common Issues**:
- Worker not running → restart: `docker compose restart notification-worker`
- Redis connection failed → check `REDIS_URL`
- Bot not responding → check bot health: `curl http://botspool-telegram:8081/health`

### API key errors

**Symptoms**: 403 Forbidden errors

**Check**:
1. API key set in all `.env.docker` files
2. No extra spaces or quotes around key
3. Header format: `X-API-Key: {key}` (not `Authorization`)

**Fix**:
```bash
# Generate new key
NEW_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Update all services
# - botspool-notification-service/.env.docker
# - botspool-telegram/.env.docker
# - botspool-todo-graph/.env.docker

# Restart all services
docker compose restart
```

### Worker stops processing

**Symptoms**: Worker container exits or stops checking

**Check**:
1. Container status: `docker ps -a | grep worker`
2. Exit code: `docker inspect botspool-notification-worker --format='{{.State.ExitCode}}'`
3. Logs: `docker logs botspool-notification-worker --tail=100`

**Common Issues**:
- Redis connection lost → check network
- Unhandled exception → check logs, fix code
- OOM killed → increase memory limit

## Production Considerations

### High Availability

- Run worker with restart policy: `restart: unless-stopped`
- Monitor worker health with external system
- Set up alerting for worker failures

### Data Persistence

- Enable Redis persistence (AOF or RDB)
- Backup Redis data regularly
- Consider PostgreSQL for long-term notification history

### Security

- Use strong API keys (32+ characters)
- Rotate keys regularly (quarterly)
- Use HTTPS for production endpoints
- Restrict network access to internal only

### Performance

- Monitor Redis memory usage
- Set max notification TTL to prevent memory bloat
- Clean up old delivery tracking data
- Index optimization for large user bases

## Migration from Immediate-Only

If upgrading from system without notifications:

1. Deploy notification service first
2. Update bot with notification endpoint
3. Update agents with notification tools
4. Test with one agent
5. Roll out to all agents
6. Monitor for issues

## Rollback Procedure

If issues occur:

```bash
# 1. Stop notification services
cd botspool-notification-service
docker compose down

# 2. Agents will continue working (tools will fail gracefully)

# 3. Fix issue

# 4. Redeploy
docker compose up -d --build
```

Agents handle notification tool failures gracefully and continue normal operation.

