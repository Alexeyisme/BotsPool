# Notification Service - Quick Start Guide

## 5-Minute Setup

### 1. Generate API Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output (e.g., `abc123def456...`)

### 2. Configure Services

Create `botspool-notification-service/.env.docker`:

```bash
REDIS_URL=redis://botspool-redis:6379/0
TELEGRAM_BOT_URL=http://botspool-telegram:8081
NOTIFICATION_API_KEY=abc123def456...  # Your generated key
WORKER_CHECK_INTERVAL_SECONDS=10
```

Add to `botspool-telegram/.env.docker`:

```bash
NOTIFICATION_PORT=8081
NOTIFICATION_API_KEY=abc123def456...  # Same key
CREDENTIAL_ENCRYPTION_KEY=$(python - <<'PY'
import base64, os
print(base64.urlsafe_b64encode(os.urandom(32)).decode())
PY
)
```

Add to `botspool-todo-graph/.env.docker`:

```bash
NOTIFICATION_SERVICE_URL=http://botspool-notification-service:8090
NOTIFICATION_API_KEY=abc123def456...  # Same key
```

### 3. Deploy

```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool

# Start notification service
cd botspool-notification-service
docker compose up -d

# Rebuild bot
cd ../botspool-telegram
docker compose up -d --build

# Rebuild agent
cd ../botspool-todo-graph
docker compose up -d --build
```

### 4. Test

In Telegram, message your bot:

```
"Send me a test notification"
```

You should receive a notification!

Or schedule a reminder:

```
"Remind me in 2 minutes to check this"
```

Wait 2 minutes and you'll receive the reminder.

> Tip: fractional hours are supported (`hours_from_now=0.033` ≈ 2 minutes).

## That's It!

Your agents can now proactively notify users.

## Verify Deployment

```bash
# Health checks
curl http://localhost:8090/health  # Notification service
curl http://localhost:8081/health  # Bot notification endpoint

# Check running services
docker ps | grep notification

# View logs
docker logs -f botspool-notification-worker
```

## Common Issues

### Notifications not arriving

```bash
# Check worker logs
docker logs botspool-notification-worker

# Check Redis
docker exec botspool-redis redis-cli ZRANGE notification:index 0 -1
```

### API key errors

Ensure the API key is **exactly the same** in all three `.env.docker` files.

## Next Steps

- Read README.md for full API documentation
- Read INTEGRATION.md for advanced integration
- Read DEPLOYMENT.md for production deployment

