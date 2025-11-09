# BotsPool Telegram Bot

Unified Telegram bot for interacting with BotsPool AI agents.

## Overview

This bot provides a unified interface to multiple AI assistants (ToDo, Email, Calendar, etc.) through a single Telegram bot. Users can select which assistant to talk to and switch between them seamlessly while maintaining separate conversation contexts for each agent.

## Prerequisites

1. Create bot with @BotFather on Telegram
2. Get bot token
3. Docker and Docker Compose installed
4. BotsPool Gateway and Redis running
5. Docker network `botspool-network` created:
   ```bash
   docker network create botspool-network
   ```

## Setup

### 1. Clone or Navigate to Repository

```bash
cd /Users/a.kislitsin/Documents/Development/BotsPool/botspool-telegram
```

### 2. Configure Environment

Copy `.env.example` to `.env.docker`:

```bash
cp .env.example .env.docker
```

Edit `.env.docker` and set:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
GATEWAY_URL=http://gateway:8000
REDIS_URL=redis://redis:6379/0
NOTIFICATION_API_KEY=shared-secret-matching-notification-service
NOTIFICATION_PORT=8081
CREDENTIAL_ENCRYPTION_KEY=$(python - <<'PY'
import base64, os
print(base64.urlsafe_b64encode(os.urandom(32)).decode())
PY
)
```

> 🔐 **Why?** `CREDENTIAL_ENCRYPTION_KEY` is used to encrypt the auto-generated password so the bot can log users back in after `/reset` without creating throwaway accounts. Store this key securely and reuse it across deployments so existing credentials remain decryptable. Keep `NOTIFICATION_API_KEY` identical to the value configured in the notification service and ToDo graph.

#### `.env` Quick Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | *(required)* |
| `GATEWAY_URL` | Base URL of the BotsPool gateway | `http://gateway:8000` |
| `REDIS_URL` | Redis connection for session caching | `redis://redis:6379/0` |
| `NOTIFICATION_API_KEY` | Shared secret with notification service | *(leave blank until set securely)* |
| `NOTIFICATION_PORT` | Local port for webhook server | `8081` |
| `CREDENTIAL_ENCRYPTION_KEY` | Base64-encoded 32-byte key for credential storage | *(generate locally)* |

### 3. Set Bot Commands in @BotFather

Send these commands to @BotFather:

```
/setcommands

start - Start the bot and register
menu - Select AI assistant
status - Show subscription and usage
reset - Clear session and start fresh
help - Show help information
```

## Deployment

### Using Docker Compose

```bash
# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f

# Check health
curl http://localhost:8080/health | jq .
```

### Integration with BotsPool Infrastructure

The bot can be integrated with the main BotsPool infrastructure. Ensure the following services are running first:

```bash
# Start infrastructure
cd /Users/a.kislitsin/Documents/Development/BotsPool
docker-compose -f docker-compose.infrastructure.yml up -d

# Start Gateway
cd botspool-gateway
docker-compose up -d

# Start ToDo Graph
cd ../botspool-todo-graph
docker-compose up -d

# Start Telegram Bot
cd ../botspool-telegram
docker-compose up -d
```

## Architecture

### Key Features

- **Auto-Registration**: New Telegram users are automatically registered with synthetic credentials
- **Credential Persistence**: Encrypted username/password stored in Redis to enable seamless re-login after `/reset`
- **Subscription-Aware**: Only shows agents available in user's subscription
- **Per-Agent Sessions**: Each agent maintains separate conversation context (compound session_id)
- **Rate Limiting**: 5 messages per minute per user
- **Token Management**: Automatic token refresh with 5-minute buffer
- **Session Persistence**: Redis-based state with 24-hour TTL (credentials stored without TTL)
- **Private Chats Only**: Only works in private chats, not groups

### Session Management

**Session ID Format**: `{chat_id}_{agent_type}`

- Keeps separate context per agent per chat
- Example: chat 12345 talking to todo = session "12345_todo"
- Switching agents creates a new session for that agent
- Previous conversations with each agent are preserved

### Redis Key Schema

```
telegram:session:{chat_id}:active_agent       -> Current agent (todo/email/etc)
telegram:session:{chat_id}:token              -> JWT access token
telegram:session:{chat_id}:refresh_token      -> JWT refresh token  
telegram:session:{chat_id}:token_expires      -> Token expiration timestamp
telegram:session:{chat_id}:user_id            -> BotsPool user UUID
telegram:session:{chat_id}:telegram_user_id   -> Telegram user ID
telegram:session:{chat_id}:password           -> Encrypted account password (no TTL)
telegram:session:{chat_id}:username           -> Stored account username (no TTL)
telegram:ratelimit:{telegram_user_id}         -> Message count (60s TTL)
```

## Commands

- `/start` - Start bot and auto-register
- `/menu` - Select AI assistant
- `/status` - Show subscription and usage
- `/reset` - Clear session and start fresh
- `/help` - Show help information

## User Flow

1. User sends `/start` to bot
2. Bot auto-registers user (creates BotsPool account with synthetic credentials)
   - If the account already exists, the bot logs in automatically using encrypted credentials
3. Bot displays menu with available assistants
4. User selects an assistant (e.g., ToDo)
5. User sends messages which are routed to the selected assistant
6. User can switch assistants anytime with `/menu`
7. Each assistant maintains its own conversation context
8. `/reset` clears tokens but keeps the encrypted credentials so `/start` restores the original account without support intervention

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run bot locally (requires .env.docker with valid credentials)
python -m src.bot.main
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio fakeredis

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_state.py -v

# Run with coverage
pytest --cov=src tests/
```

## Monitoring

### Health Check Endpoint

The bot exposes a health check endpoint on port 8080:

```bash
curl http://localhost:8080/health
```

Response:
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

### Logs

View bot logs:

```bash
docker-compose logs -f telegram-bot
```

Logs are structured JSON with:
- timestamp
- level
- service name
- message
- contextual information (chat_id, telegram_user_id, agent)

## Troubleshooting

### Bot Not Responding

1. Check if bot is running:
   ```bash
   docker-compose ps
   ```

2. Check logs for errors:
   ```bash
   docker-compose logs --tail=100 telegram-bot
   ```

3. Verify bot token is correct in `.env.docker`

4. Check Gateway is accessible:
   ```bash
   docker exec botspool-telegram curl http://gateway:8000/health/status
   ```

### Redis Connection Issues

```bash
# Check Redis is running
docker ps | grep redis

# Test Redis connection
docker exec botspool-telegram python -c "import redis; r=redis.from_url('redis://redis:6379/0'); print(r.ping())"
```

### Gateway Connection Issues

```bash
# Check Gateway is running
curl http://localhost:8000/health/status

# From bot container
docker exec botspool-telegram curl http://gateway:8000/health/status
```

### User Registration Fails

- Check Gateway `/api/v1/auth/register` endpoint is working
- Verify JWT keys are configured in Gateway
- Check Gateway logs for registration errors

### Rate Limiting

If users are being rate limited unexpectedly:

1. Check `MESSAGE_RATE_LIMIT` in `.env.docker`
2. Clear rate limit for a user:
   ```bash
   docker exec botspool-redis redis-cli DEL telegram:ratelimit:USER_ID
   ```

## Security Considerations

- **Synthetic Credentials**: Auto-registered users get random passwords not exposed to them
- **JWT Tokens**: Stored in Redis with 24-hour TTL
- **Rate Limiting**: Prevents abuse (5 messages/minute per user)
- **Private Chats Only**: No group chat support (reduces attack surface)
- **Input Validation**: All user input validated before processing
- **Structured Logging**: Audit trail for all user actions

## API Integration

### Gateway Endpoints Used

- `POST /api/v1/auth/register` - Auto-register users
- `POST /api/v1/auth/refresh` - Refresh access tokens
- `GET /api/v1/graphs` - Get available graphs
- `POST /api/v1/chat/{graph_type}` - Send messages to agents
- `GET /api/v1/subscription/status` - Get subscription info

### Authentication Flow

1. User starts bot (`/start`)
2. Bot calls Gateway registration endpoint
3. Gateway returns access_token and refresh_token
4. Bot stores tokens in Redis
5. Bot uses access_token for all subsequent requests
6. Bot refreshes token when < 5 minutes remaining

## Contributing

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for all functions
- Keep functions focused and small

### Testing

- Write tests for all new features
- Maintain test coverage above 80%
- Use mocking for external dependencies

## Project Structure

```
botspool-telegram/
├── src/
│   ├── bot/
│   │   ├── handlers/         # Command and message handlers
│   │   ├── main.py          # Main bot application
│   │   ├── keyboards.py      # Inline keyboard builders
│   │   ├── state.py         # Redis state management
│   │   └── rate_limiter.py  # Rate limiting
│   ├── gateway/
│   │   ├── client.py        # Gateway API client
│   │   └── auth.py          # Authentication helpers
│   ├── health/
│   │   └── server.py        # Health check endpoint
│   ├── config.py            # Configuration
│   ├── models.py            # Data models
│   └── logging_config.py    # Logging setup
├── tests/                   # Unit and integration tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## License

Part of the BotsPool project.

## Support

For issues or questions:
- Check the logs first
- Review this README
- Check BotsPool documentation
- Create an issue with logs and steps to reproduce

