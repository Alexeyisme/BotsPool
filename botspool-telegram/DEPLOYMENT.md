# Telegram Bot Deployment Guide

## Quick Start

### Prerequisites

1. **Create Telegram Bot**
   - Open Telegram and find @BotFather
   - Send `/newbot` and follow instructions
   - Copy the bot token

2. **Set Bot Commands** (Optional but recommended)
   - Send `/setcommands` to @BotFather
   - Paste:
   ```
   start - Start the bot and register
   menu - Select AI assistant
   status - Show subscription and usage
   reset - Clear session and start fresh
   help - Show help information
   ```

3. **Ensure Infrastructure is Running**
   ```bash
   cd /Users/a.kislitsin/Documents/Development/BotsPool
   docker-compose -f docker-compose.infrastructure.yml ps
   ```
   
   Verify these services are running:
   - `postgres-gateway` (port 5432)
   - `postgres-todograph` (port 5433)
   - `redis` (port 6379)

4. **Ensure Gateway is Running**
   ```bash
   cd botspool-gateway
   docker-compose ps
   ```

5. **Ensure ToDo Graph is Running**
   ```bash
   cd ../botspool-todo-graph
   docker-compose ps
   ```

### Configuration

1. **Edit Environment File**
   ```bash
   cd ../botspool-telegram
   # Note: .env.docker is in .gitignore, manually create it
   ```

2. **Create `.env.docker` with your bot token:**
   ```bash
   # Telegram
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   
   # Gateway
   GATEWAY_URL=http://gateway:8000
   
   # Redis
   REDIS_URL=redis://redis:6379/0
   CREDENTIAL_ENCRYPTION_KEY=$(python - <<'PY'
import base64, os
print(base64.urlsafe_b64encode(os.urandom(32)).decode())
PY
)
   
   # Bot settings
   DEFAULT_AGENT=todo
   SESSION_TIMEOUT=86400
   MESSAGE_RATE_LIMIT=5
   
   # Health check
   HEALTH_CHECK_PORT=8080
   
   # Logging
   LOG_LEVEL=INFO
   ```

   > 💡 Keep `CREDENTIAL_ENCRYPTION_KEY` safe. It encrypts the auto-generated Telegram user password so `/reset` can clear sessions while preserving credentials for the next `/start`.

### Deployment

**Option 1: Standalone Deployment**

```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool/botspool-telegram
docker-compose up -d
```

**Option 2: Integrated Deployment**

```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool
docker-compose -f docker-compose.telegram-integration.yml up -d
```

### Verification

1. **Check Health**
   ```bash
   curl http://localhost:8080/health | jq .
   ```
   
   Expected output:
   ```json
   {
     "status": "healthy",
     "service": "telegram-bot",
     "dependencies": {
       "redis": "healthy",
       "gateway": "healthy"
     }
   }
   ```

2. **Check Logs**
   ```bash
   docker-compose logs -f telegram-bot
   ```
   
   Look for:
   - "Redis connected"
   - "Gateway connected"
   - "Bot initialization complete"
   - "Bot started polling..."

3. **Test Bot in Telegram**
   - Open Telegram
   - Search for your bot by username
   - Send `/start`
   - You should see a welcome message with agent selection buttons (if already registered, the bot will automatically log you back in using the stored credentials)

## Troubleshooting

### Bot doesn't respond

**Issue**: No response from bot in Telegram

**Diagnosis:**
```bash
# Check if container is running
docker ps | grep botspool-telegram

# Check logs
docker-compose logs --tail=50 telegram-bot

# Check bot token
docker exec botspool-telegram env | grep TELEGRAM_BOT_TOKEN
```

**Solutions:**
- Verify bot token is correct
- Ensure container is running
- Check Telegram API is reachable (network issues)

### Gateway connection failed

**Issue**: Bot logs show "Failed to connect to Gateway"

**Diagnosis:**
```bash
# From bot container
docker exec botspool-telegram curl http://gateway:8000/health/status

# Check Gateway is running
docker ps | grep gateway
cd ../botspool-gateway && docker-compose ps
```

**Solutions:**
- Ensure Gateway is running
- Verify `botspool-network` exists: `docker network ls`
- Check Gateway health: `curl http://localhost:8000/health/status`

### Redis connection failed

**Issue**: Bot logs show Redis connection errors

**Diagnosis:**
```bash
# Check Redis is running
docker ps | grep redis

# Test connection from bot
docker exec botspool-telegram python -c "import redis; r=redis.from_url('redis://redis:6379/0'); print(r.ping())"
```

**Solutions:**
- Ensure Redis is running: `docker-compose -f docker-compose.infrastructure.yml up -d redis`
- Verify network connectivity
- Check REDIS_URL in .env.docker

### Registration fails

**Issue**: Users get "Sorry, I couldn't register you" message

**Diagnosis:**
```bash
# Check Gateway logs
cd ../botspool-gateway
docker-compose logs --tail=100 | grep register

# Test registration endpoint
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "test_user",
    "email": "test@example.com",
    "password": "TestPass123!",
    "display_name": "Test User",
    "frontend_type": "telegram"
  }'
```

**Solutions:**
- Ensure Gateway database is initialized
- Check JWT keys are configured in Gateway
- Verify PostgreSQL is accessible

## Advanced Configuration

### Rate Limiting

Adjust rate limits in `.env.docker`:
```bash
MESSAGE_RATE_LIMIT=10  # Increase to 10 messages/minute
```

### Session Timeout

Adjust session timeout:
```bash
SESSION_TIMEOUT=172800  # 48 hours instead of 24
```

### Logging Level

For debugging:
```bash
LOG_LEVEL=DEBUG
```

For production:
```bash
LOG_LEVEL=INFO
```

## Monitoring

### Health Checks

Automated health checks run every 30 seconds. View status:
```bash
docker inspect botspool-telegram | jq '.[0].State.Health'
```

### Logs

View structured JSON logs:
```bash
docker-compose logs -f telegram-bot | jq .
```

Filter by level:
```bash
docker-compose logs telegram-bot | grep ERROR
```

### Metrics

Redis keys for monitoring:
```bash
# Check active sessions
docker exec botspool-redis redis-cli KEYS "telegram:session:*" | wc -l

# Check rate limits
docker exec botspool-redis redis-cli KEYS "telegram:ratelimit:*"
```

## Maintenance

### Update Bot

```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool/botspool-telegram

# Pull latest changes (if using git)
git pull

# Rebuild and restart
docker-compose build
docker-compose up -d
```

### Clear User Session

```bash
# Clear specific user session (get chat_id from logs)
docker exec botspool-redis redis-cli KEYS "telegram:session:CHAT_ID:*" | xargs docker exec botspool-redis redis-cli DEL
```

### Backup

Redis data is ephemeral (sessions). No backup needed unless you want to preserve active sessions during maintenance.

For maintenance with session preservation:
```bash
# Save Redis data
docker exec botspool-redis redis-cli SAVE

# Stop bot
docker-compose down

# Update/maintain

# Start bot (sessions restored from Redis persistence)
docker-compose up -d
```

## Production Checklist

- [ ] Bot token configured
- [ ] Gateway accessible from bot container
- [ ] Redis accessible from bot container
- [ ] Health checks passing
- [ ] Logs show successful initialization
- [ ] Test user registration works
- [ ] Test message routing works
- [ ] Test agent switching works
- [ ] Rate limiting verified
- [ ] Error messages are user-friendly
- [ ] Monitoring configured
- [ ] Backup strategy defined (if needed)

## Support

If issues persist:
1. Collect logs: `docker-compose logs telegram-bot > bot-logs.txt`
2. Check Gateway logs: `cd ../botspool-gateway && docker-compose logs > gateway-logs.txt`
3. Verify all services: `docker ps -a`
4. Check network: `docker network inspect botspool-network`
5. Review this guide and README.md
6. Create issue with logs and reproduction steps

