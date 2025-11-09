# Telegram Bot Quick Start Guide

## Fast Setup (5 Minutes)

### Step 1: Create Your Bot (2 min)

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Follow prompts to name your bot
4. **Copy the bot token** (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### Step 2: Configure Bot Token (1 min)

```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool/botspool-telegram

# Create .env.docker file (it's in .gitignore)
cat > .env.docker << 'EOF'
TELEGRAM_BOT_TOKEN=YOUR_TOKEN_HERE
GATEWAY_URL=http://gateway:8000
REDIS_URL=redis://redis:6379/0
CREDENTIAL_ENCRYPTION_KEY=$(python - <<'PY'
import base64, os
print(base64.urlsafe_b64encode(os.urandom(32)).decode())
PY
)
DEFAULT_AGENT=todo
SESSION_TIMEOUT=86400
MESSAGE_RATE_LIMIT=5
HEALTH_CHECK_PORT=8080
LOG_LEVEL=INFO
EOF

# Replace YOUR_TOKEN_HERE with your actual bot token
```

### Step 3: Ensure Infrastructure is Running (1 min)

```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool

# Check what's running
docker ps

# If not running, start infrastructure
docker-compose -f docker-compose.infrastructure.yml up -d

# Start Gateway (if not running)
cd botspool-gateway && docker-compose up -d

# Start ToDo Graph (if not running)
cd ../botspool-todo-graph && docker-compose up -d
```

### Step 4: Start the Bot (1 min)

```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool/botspool-telegram

# Build and start
docker-compose up -d

# Watch logs
docker-compose logs -f
```

Look for these success messages:
- ✅ "Redis connected"
- ✅ "Gateway connected"
- ✅ "Bot initialization complete"
- ✅ "Bot started polling..."

### Step 5: Test Your Bot

1. Open Telegram
2. Search for your bot by username
3. Send `/start`
4. You should see (existing users will be logged back in automatically):
   ```
   Welcome to BotsPool, [Your Name]! 🎉

   I'm your unified AI assistant platform.
   I can help you with tasks, emails, calendar, and more!

   Select an assistant below to get started:
   
   [📝 ToDo Assistant]
   [ℹ️ Status] [❓ Help]
   ```

5. Click "📝 ToDo Assistant"
6. Send a message: "Create a task to test the bot"
7. You should get a response from the ToDo agent!

## Troubleshooting

### Bot doesn't respond to /start

**Check bot is running:**
```bash
docker ps | grep telegram
```

**Check logs for errors:**
```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool/botspool-telegram
docker-compose logs --tail=50
```

### "Gateway not ready" error in logs

**Check Gateway is running:**
```bash
curl http://localhost:8000/health/status
```

**If not, start it:**
```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool/botspool-gateway
docker-compose up -d
```

### "Redis connection failed"

**Check Redis is running:**
```bash
docker ps | grep redis
```

**If not, start it:**
```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool
docker-compose -f docker-compose.infrastructure.yml up -d redis
```

## What's Next?

- Send messages to test the ToDo agent
- Try `/menu` to see agent selection
- Try `/status` to see your subscription
- Try `/help` for command list
- Check logs to see how it works: `docker-compose logs -f`

## Full Documentation

- [README.md](README.md) - Complete documentation
- [DEPLOYMENT.md](DEPLOYMENT.md) - Detailed deployment guide
- [INTEGRATION_NOTES.md](INTEGRATION_NOTES.md) - Integration architecture

## Common Commands

```bash
# View logs
docker-compose logs -f telegram-bot

# Restart bot
docker-compose restart telegram-bot

# Stop bot
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Check health
curl http://localhost:8080/health | jq .
```

Enjoy your BotsPool Telegram Bot! 🚀

