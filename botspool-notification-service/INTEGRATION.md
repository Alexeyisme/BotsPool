# Notification Service Integration Guide

## Overview

This guide explains how to integrate the Notification Service with BotsPool agents and frontends.

## For AI Agent Developers

### Adding Notification Tools to Your Agent

1. **Import notification tools**:

```python
from tools.notification_tools import (
    send_notification,
    schedule_reminder,
    cancel_reminder,
    list_user_reminders
)
```

2. **Register with LangGraph model**:

```python
response = self.model.bind_tools(
    [YourExistingTool, send_notification, schedule_reminder],
    parallel_tool_calls=False
).invoke(messages)
```

3. **Configure environment**:

Add to your agent's `.env.docker`:
```bash
NOTIFICATION_SERVICE_URL=http://botspool-notification-service:8090
NOTIFICATION_API_KEY=your-api-key
```

### Tool Usage Examples

#### Immediate Notification

```python
# User: "Let me know when you're done"
# Agent: Processes task, then calls:
send_notification(
    message="Task processing complete!",
    priority="normal",
    notification_type="info"
)
# Agent responds: "I'll notify you when done"
# Later: User receives notification
```

#### Scheduled Reminder

```python
# User: "Remind me tomorrow at 9 AM to review this"
# Agent: Calculates time and calls:
schedule_reminder(
    message="Review the deployment documentation",
    hours_from_now=14  # If current time is 7 PM
)
# Agent responds: "I'll remind you in 14 hours"
# Tomorrow at 9 AM: User receives reminder
```

#### Task Deadline Alert

```python
# Agent detects task due in 1 hour
# Agent proactively calls:
send_notification(
    message="⏰ Your task 'Deploy BotsPool' is due in 1 hour!",
    priority="high",
    notification_type="alert"
)
# User receives alert without asking
```

### Context Extraction

Tools automatically extract `chat_id` and `user_id` from LangGraph context:

```python
# Tools access config passed by LangGraph
def send_notification(message: str, config: dict = None):
    # Extract from metadata
    chat_id = config.get("metadata", {}).get("chat_id")
    user_id = config.get("user_id")
    
    # Or extract from session_id
    session_id = config.get("session_id")  # e.g., "1153284_todo"
    chat_id = int(session_id.split('_')[0])
```

**Metadata Structure** (passed by frontends):
```json
{
  "metadata": {
    "frontend": "telegram",
    "chat_id": "1153284",
    "telegram_user_id": "1153284"
  }
}
```

## For Frontend Developers

### Adding Notification Endpoint to Your Bot

1. **Create notification endpoint**:

```python
from fastapi import FastAPI, HTTPException, Header

notification_app = FastAPI()

@notification_app.post("/api/v1/notify")
async def receive_notification(
    notification: NotificationRequest,
    x_api_key: str = Header(...)
):
    # Verify API key
    if x_api_key != NOTIFICATION_API_KEY:
        raise HTTPException(403, "Invalid API key")
    
    # Send to user via your frontend
    await send_to_user(
        chat_id=notification.chat_id,
        message=notification.message
    )
    
    return {"status": "delivered"}
```

2. **Run in background**:

```python
# Start FastAPI server in background thread
import uvicorn
from threading import Thread

def run_notification_server():
    uvicorn.run(notification_app, host="0.0.0.0", port=8081)

Thread(target=run_notification_server, daemon=True).start()
```

3. **Update Docker configuration**:

```yaml
ports:
  - "8081:8081"  # Notification endpoint
```

4. **Configure environment**:

```bash
NOTIFICATION_PORT=8081
NOTIFICATION_API_KEY=your-api-key
```

### Request Format from Notification Service

```json
{
  "chat_id": 1153284,
  "message": "Your task is complete!",
  "agent": "todo",
  "notification_type": "reminder",
  "priority": "normal"
}
```

### Response Format to Notification Service

```json
{
  "status": "delivered",
  "delivered_at": "2025-11-06T12:00:00Z"
}
```

## Network Configuration

### Docker Network

All services must be on `botspool-network`:

```bash
docker network create botspool-network
```

### Service Discovery

Services communicate via Docker DNS:
- Notification Service: `http://botspool-notification-service:8090`
- Telegram Bot: `http://botspool-telegram:8081`
- Discord Bot: `http://botspool-discord:8082` (future)

## Security

### API Key Configuration

Use the same API key across all services:

**Notification Service** (`.env.docker`):
```bash
NOTIFICATION_API_KEY=your-secure-random-key
```

**Telegram Bot** (`.env.docker`):
```bash
NOTIFICATION_API_KEY=your-secure-random-key
```

**ToDo Agent** (`.env.docker`):
```bash
NOTIFICATION_API_KEY=your-secure-random-key
```

### Generate Secure API Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Rate Limiting

### Default Limits

- 10 notifications per hour per user
- Applies to both immediate and scheduled notifications
- Tracked in Redis with 1-hour window

### Customization

Update in `config.py`:

```python
MAX_NOTIFICATIONS_PER_HOUR = 20  # Increase limit
```

### Rate Limit Behavior

When limit exceeded:
- Immediate notifications: Return 503 error
- Scheduled notifications: Delayed until rate limit resets

## Error Handling

### Delivery Failures

**Retries**: 3 attempts with exponential backoff

**Permanent Failures**:
- User blocked bot
- Invalid chat_id
- Frontend permanently unavailable

**Temporary Failures**:
- Network timeout
- Frontend temporarily down
- Rate limit exceeded

### Error Codes

| Error | Status | Description |
|-------|--------|-------------|
| Invalid API key | 403 | Authentication failed |
| Rate limit exceeded | 429 | Too many notifications |
| Notification not found | 404 | Invalid notification ID |
| Invalid request | 400 | Validation error |
| Delivery failed | 503 | Frontend unavailable |

## Monitoring

### Key Metrics

- Notifications sent per hour
- Scheduled notifications pending
- Delivery success rate
- Average delivery time
- Failed notifications

### Logs

**Structured logging** with fields:
- `notification_id`: Unique identifier
- `user_id`: BotsPool user UUID
- `chat_id`: Frontend chat ID
- `agent`: Source agent
- `status`: Delivery status
- `scheduled_for`: Scheduled time (if applicable)

### Health Checks

```bash
# Service health
curl http://localhost:8090/health

# Redis connectivity
docker exec botspool-notification-service python -c \
  "import redis; r=redis.from_url('redis://botspool-redis:6379/0'); print(r.ping())"
```

## Data Flow

### Immediate Notification

```
1. Agent calls send_notification tool
2. Tool → POST /api/v1/notifications
3. Service validates request
4. Dispatcher checks rate limit
5. Dispatcher → POST {bot_url}/api/v1/notify
6. Bot sends to user
7. Bot confirms delivery
8. Service logs success
```

### Scheduled Notification

```
1. Agent calls schedule_reminder tool
2. Tool → POST /api/v1/notifications/schedule
3. Service stores in Redis:
   - Key: notification:scheduled:{timestamp}:{id}
   - Sorted set: notification:index
4. Service returns notification_id
5. Worker checks Redis every 10s
6. When due:
   - Worker retrieves notification
   - Dispatcher sends to bot
   - Bot delivers to user
   - Service marks as sent
   - Removed from Redis
```

## Best Practices

### For Agents

1. **Use descriptive messages**: "Reminder: Review deployment" not just "Review"
2. **Set appropriate priority**: Use "high" sparingly
3. **Handle tool errors**: Check return value and retry if needed
4. **Respect user preferences**: Don't spam with notifications
5. **Provide context**: Include task details in notification message

### For Frontends

1. **Validate API key**: Always verify X-API-Key header
2. **Handle delivery failures**: Return appropriate error codes
3. **Format messages**: Add icons and formatting for better UX
4. **Log delivery**: Track successful and failed deliveries
5. **Graceful degradation**: Handle notification service downtime

## Troubleshooting

### Notifications not arriving

1. Check worker is running: `docker ps | grep worker`
2. Check logs: `docker logs botspool-notification-worker`
3. Verify scheduled time: `redis-cli ZRANGE notification:index 0 -1 WITHSCORES`
4. Check rate limit: `redis-cli GET notification:ratelimit:{user_id}`

### API key errors

1. Verify key matches across all services
2. Check header format: `X-API-Key`
3. Ensure no extra spaces or quotes

### Worker not processing

1. Check Redis connection
2. Verify `WORKER_CHECK_INTERVAL_SECONDS` setting
3. Check for errors in worker logs
4. Restart worker container

## Support

For issues or questions:
- Check logs: `docker compose logs`
- Review Redis data: `redis-cli`
- Verify configuration: `docker exec {container} env | grep NOTIFICATION`

