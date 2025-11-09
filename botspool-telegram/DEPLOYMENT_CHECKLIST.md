# Telegram Bot Deployment Checklist

## Pre-Deployment Checklist

### 1. Bot Creation on Telegram
- [ ] Created bot with @BotFather
- [ ] Copied bot token
- [ ] Set bot username
- [ ] Set bot commands (optional):
  ```
  start - Start the bot and register
  menu - Select AI assistant
  status - Show subscription and usage
  reset - Clear session and start fresh
  help - Show help information
  ```

### 2. Infrastructure Verification
- [ ] Docker network exists: `docker network ls | grep botspool-network`
  - If not: `docker network create botspool-network`
- [ ] PostgreSQL running (Gateway): `docker ps | grep postgres-gateway`
- [ ] PostgreSQL running (ToDo Graph): `docker ps | grep postgres-todograph`
- [ ] Redis running: `docker ps | grep redis`
- [ ] Gateway running: `curl http://localhost:8000/health/status`
- [ ] ToDo Graph running: `curl http://localhost:8011/health`

### 3. Configuration
- [ ] Created `.env.docker` file (copy from `.env.example`)
- [ ] Set `TELEGRAM_BOT_TOKEN` in `.env.docker`
- [ ] Verified `GATEWAY_URL=http://gateway:8000`
- [ ] Verified `REDIS_URL=redis://redis:6379/0`
- [ ] Generated and set `CREDENTIAL_ENCRYPTION_KEY` (32-byte Fernet key)
- [ ] Adjusted rate limits if needed (default: 5 msg/min)

## Deployment Steps

### Option A: Standalone Deployment

```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool/botspool-telegram

# 1. Build the image
docker-compose build

# 2. Start the service
docker-compose up -d

# 3. Check logs
docker-compose logs -f telegram-bot
```

**Expected log messages:**
- ✅ "Initializing bot services..."
- ✅ "Redis connected"
- ✅ "Gateway connected"
- ✅ "Bot initialization complete"
- ✅ "Bot started polling..."

### Option B: Integrated Deployment

```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool

# Start telegram bot with existing infrastructure
docker-compose -f docker-compose.telegram-integration.yml up -d

# Check logs
docker logs -f botspool-telegram
```

## Post-Deployment Verification

### 1. Health Check
```bash
curl http://localhost:8080/health | jq .
```

**Expected response:**
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

- [ ] Health endpoint returns 200 OK
- [ ] Redis dependency shows "healthy"
- [ ] Gateway dependency shows "healthy"

### 2. Container Health
```bash
docker ps | grep botspool-telegram
```

- [ ] Container is running (not restarting)
- [ ] Health status shows "healthy"
- [ ] Uptime > 1 minute

### 3. Log Verification
```bash
docker-compose logs --tail=100 telegram-bot
```

- [ ] No ERROR messages
- [ ] Redis connection successful
- [ ] Gateway connection successful
- [ ] Bot polling started

### 4. Network Connectivity
```bash
# From bot container to Gateway
docker exec botspool-telegram curl http://gateway:8000/health/status

# From bot container to Redis
docker exec botspool-telegram python -c "import redis; r=redis.from_url('redis://redis:6379/0'); print(r.ping())"
```

- [ ] Gateway reachable from bot
- [ ] Redis reachable from bot

## Functional Testing

### 5. User Registration
1. Open Telegram
2. Search for your bot by username
3. Send `/start`

**Expected:**
- [ ] Bot responds within 2 seconds
- [ ] Welcome message displays
- [ ] Agent selection keyboard appears
- [ ] Buttons show: "📝 ToDo Assistant", "ℹ️ Status", "❓ Help"
- [ ] Existing users are logged in automatically without the support warning

**Check logs:**
- [ ] "User started bot" log entry
- [ ] No registration errors
- [ ] Token stored successfully

### 6. Agent Selection
1. Click "📝 ToDo Assistant" button

**Expected:**
- [ ] Message changes to "Switched to 📝 ToDo Assistant!"
- [ ] Instruction to send a message appears

**Check Redis:**
```bash
docker exec botspool-redis redis-cli GET "telegram:session:YOUR_CHAT_ID:active_agent"
```
- [ ] Shows "todo"

### 7. Message Routing
1. Send message: "Create a task to buy groceries"

**Expected:**
- [ ] Typing indicator appears
- [ ] Response received within 5 seconds
- [ ] Response is relevant to task creation

**Check logs:**
```bash
docker-compose logs --tail=50 telegram-bot | grep "Message processed"
```
- [ ] Message processed log entry
- [ ] No errors
- [ ] Tokens counted

**Check Gateway logs:**
```bash
cd ../botspool-gateway
docker-compose logs --tail=50 | grep "chat/todo"
```
- [ ] Gateway received chat request
- [ ] Routed to todo graph

### 8. Rate Limiting
1. Send 6 messages rapidly

**Expected:**
- [ ] First 5 messages process normally
- [ ] 6th message gets: "⏳ Please slow down! Try again in X seconds."

### 9. Status Command
1. Send `/status`

**Expected:**
- [ ] Shows current assistant
- [ ] Shows subscription tier
- [ ] Shows usage statistics
- [ ] Lists available assistants

### 10. Menu Command
1. Send `/menu`

**Expected:**
- [ ] Agent selection keyboard appears
- [ ] Only subscribed agents shown
- [ ] Can select different agent

### 11. Help Command
1. Send `/help`

**Expected:**
- [ ] Shows all commands
- [ ] Shows usage instructions
- [ ] Clear and helpful

### 12. Reset Command
1. Send `/reset`

**Expected:**
- [ ] Confirmation message
- [ ] Session cleared
- [ ] /start required to continue

**Check Redis:**
```bash
docker exec botspool-redis redis-cli KEYS "telegram:session:YOUR_CHAT_ID:*"
```
- [ ] No keys found (session cleared)

## Multi-User Testing

### 13. Concurrent Users
1. Have 2+ people start the bot simultaneously

**Expected:**
- [ ] Each user gets unique session
- [ ] No cross-user data leakage
- [ ] Each user can select different agents
- [ ] Messages routed correctly per user

**Check Redis:**
```bash
docker exec botspool-redis redis-cli KEYS "telegram:session:*:active_agent"
```
- [ ] Multiple session keys present
- [ ] Each chat_id is unique

## Performance Testing

### 14. Response Time
- [ ] Registration: < 2 seconds
- [ ] Menu display: < 1 second
- [ ] Message response: < 5 seconds (depends on agent)
- [ ] Status display: < 2 seconds

### 15. Resource Usage
```bash
docker stats botspool-telegram --no-stream
```

- [ ] CPU: < 50% under normal load
- [ ] Memory: < 512MB
- [ ] No memory leaks (stable over time)

## Error Handling Testing

### 16. Gateway Unavailable
```bash
# Stop Gateway temporarily
cd /Users/a.kislitsin/Documents/Development/BotsPool/botspool-gateway
docker-compose stop

# Try to send message in Telegram
```

**Expected:**
- [ ] Bot shows: "Service temporarily unavailable"
- [ ] Bot doesn't crash
- [ ] After Gateway restart, bot recovers

### 17. Redis Unavailable
```bash
# Stop Redis temporarily
cd /Users/a.kislitsin/Documents/Development/BotsPool
docker-compose -f docker-compose.infrastructure.yml stop redis

# Try to send message
```

**Expected:**
- [ ] Bot handles gracefully
- [ ] Error logged
- [ ] After Redis restart, new sessions work

### 18. Invalid Token
```