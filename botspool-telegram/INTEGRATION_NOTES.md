# BotsPool Integration Notes

## Architecture Integration

The Telegram bot integrates with the BotsPool platform as follows:

```
┌──────────────┐
│   Telegram   │
│    Users     │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  Telegram Bot    │  ← This service
│  (Port 8080)     │
└──────┬───────────┘
       │
       ├─────────────┐
       │             │
       ▼             ▼
┌──────────┐   ┌─────────────┐
│  Redis   │   │   Gateway   │
│  :6379   │   │   :8000     │
└──────────┘   └──────┬──────┘
                      │
                      ▼
               ┌──────────────┐
               │  ToDo Graph  │
               │    :8011     │
               └──────────────┘
```

## Key Integration Points

### 1. Authentication Flow

**Bot → Gateway Registration:**
- Bot calls `POST /api/v1/auth/register` with synthetic credentials
- Credentials format:
  - username: `telegram_{telegram_id}`
  - email: `telegram_{telegram_id}@botspool.internal`
  - password: randomly generated (not exposed to user)
- Passwords are encrypted with `CREDENTIAL_ENCRYPTION_KEY` and stored in Redis for seamless re-login after `/reset`
- On subsequent `/start`, the bot calls `POST /api/v1/auth/login` with the stored credentials before attempting a new registration

**Token Management:**
- Tokens stored in Redis with chat_id as key
- Automatic refresh when < 5 minutes remaining
- Refresh token stored separately for token renewal

### 2. Session Management

**Compound Session IDs:**
- Format: `{chat_id}_{agent_type}`
- Example: `12345_todo`, `12345_email`
- Enables per-agent conversation context
- Each agent sees only its own conversation history

**Redis Key Pattern:**
```
telegram:session:{chat_id}:active_agent        → Current agent
telegram:session:{chat_id}:token               → Access token
telegram:session:{chat_id}:refresh_token       → Refresh token
telegram:session:{chat_id}:token_expires       → Expiration timestamp
telegram:session:{chat_id}:user_id             → BotsPool user UUID
telegram:session:{chat_id}:telegram_user_id    → Telegram user ID
telegram:session:{chat_id}:password            → Encrypted account password (no TTL)
telegram:session:{chat_id}:username            → Stored account username (no TTL)
```

### 3. Message Routing

**Flow:**
1. User sends message in Telegram
2. Bot checks rate limit (Redis)
3. Bot gets active agent from Redis
4. Bot calls Gateway with compound session_id
5. Gateway routes to appropriate graph
6. Graph processes with LangGraph (PostgreSQL checkpointer)
7. Response sent back through Gateway
8. Bot sends response to Telegram user

**API Call:**
```http
POST http://gateway:8000/api/v1/chat/{agent_type}
Authorization: Bearer {jwt_token}

{
  "message": "user message",
  "user_id": "telegram_user_id",
  "session_id": "{chat_id}_{agent_type}",
  "metadata": {
    "frontend": "telegram",
    "chat_id": "chat_id"
  }
}
```

### 4. Subscription Awareness

**Graph Availability:**
- Bot fetches available graphs from Gateway: `GET /api/v1/graphs`
- Keyboard buttons show only accessible agents
- Based on user's subscription tier
- Graceful handling if user tries unavailable agent

### 5. Rate Limiting

**Two-Layer Approach:**
1. **Bot-Level** (5 messages/minute per user)
   - Implemented in bot using Redis
   - Prevents spamming Gateway
   - User-friendly error messages

2. **Gateway-Level** (as per subscription)
   - Enforced by Gateway
   - Returns 429 status code
   - Bot handles and informs user

## Network Configuration

### Docker Network

All services must be on `botspool-network`:

```bash
docker network create botspool-network
```

### Service Names (DNS)

- `gateway` → BotsPool Gateway (port 8000)
- `redis` → Redis (port 6379)
- `postgres-gateway` → Gateway PostgreSQL (port 5432)
- `postgres-todograph` → ToDo Graph PostgreSQL (port 5433)

### External Ports

- Bot health check: `localhost:8080`
- Gateway API: `localhost:8000`
- Redis (for debugging): `localhost:6379`

## Data Flow Examples

### Example 1: New User First Message

1. User: `/start` in Telegram
2. Bot: Check Redis for token → None found
3. Bot: Call Gateway `POST /api/v1/auth/register`
4. Gateway: Create user, return tokens
5. Bot: Store tokens, encrypted password, and username in Redis
6. Bot: Show welcome + agent selection keyboard
7. User: Selects "ToDo" agent
8. Bot: Store active_agent=todo in Redis
9. User: "Create a task to buy milk"
10. Bot: Check rate limit → OK
11. Bot: Call Gateway `POST /api/v1/chat/todo?user_id=...`
12. Gateway: Route to ToDo Graph with session_id="chatid_todo"
13. ToDo Graph: Process with LangGraph, save to PostgreSQL
14. Response: "I've created a task..."
15. Bot: Send response to Telegram user

### Example 2: Returning User Switches Agent

1. User: `/menu` in Telegram
2. Bot: Fetch available graphs from Gateway
3. Bot: Show keyboard with available agents
4. User: Selects "Email" agent
5. Bot: Update active_agent=email in Redis
6. Bot: Confirm switch
7. User: "Draft email to John"
8. Bot: Check rate limit → OK
9. Bot: Call Gateway with session_id="chatid_email"
10. Gateway: Route to Email Graph
11. Email Graph: New conversation context (different session_id)
12. Response: "I'll help you draft that email..."
13. Bot: Send response to user

**Returning user with `/start`:**
1. User: `/start` after `/reset`
2. Bot: Finds stored encrypted password + username
3. Bot: Call Gateway `POST /api/v1/auth/login`
4. Gateway: Returns new tokens
5. Bot: Updates Redis session keys (credentials persist)
6. Bot: Shows welcome menu (no temp account required)

### Example 3: Token Refresh

1. User: Sends message after 55 minutes
2. Bot: Check token expiry → < 5 minutes left
3. Bot: Get refresh_token from Redis
4. Bot: Call Gateway `POST /api/v1/auth/refresh`
5. Gateway: Validate refresh token, issue new tokens
6. Bot: Store new tokens in Redis
7. Bot: Proceed with original message routing

## Error Handling

### Gateway Errors

| Error Code | Bot Response |
|------------|--------------|
| 401 | "Session expired, please /start again" |
| 403 | "You don't have access to this agent" |
| 429 | "Rate limit reached, please wait" |
| 503 | "Agent temporarily unavailable, try another" |
| 5xx | "Something went wrong, try again later" |

### Network Errors

- Connection timeout → "Service temporarily unavailable"
- DNS resolution failed → Health check catches, bot stays down
- Gateway unreachable → Bot startup retries 5 times with backoff

## Monitoring Integration

### Health Checks

Bot exposes health endpoint for orchestration:

```bash
curl http://localhost:8080/health
```

Returns:
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

### Logging

Structured JSON logs include:
- timestamp
- level (INFO, ERROR, etc.)
- service: "telegram-bot"
- message
- context: chat_id, telegram_user_id, agent

Can be aggregated with Gateway/Graph logs for full request tracing.

### Metrics

Track via Redis:
- Active sessions: `KEYS telegram:session:*`
- Rate limit hits: `KEYS telegram:ratelimit:*`
- Session count: Indicator of active users

## Security Considerations

### Synthetic Credentials

- Users never see their BotsPool password
- Prevents credential stuffing attacks
- Users can't log in via web without password reset

### Token Storage

- Tokens in Redis with 24h TTL
- Automatic cleanup on expiry
- No tokens in logs or responses

### Input Validation

- All user input validated before Gateway calls
- Rate limiting prevents abuse
- Private chat only (no groups)

### Network Security

- Bot only accessible via Telegram API
- Internal communication on Docker network
- Health endpoint on localhost only (mapped for monitoring)

## Deployment Considerations

### Startup Order

1. PostgreSQL (Gateway & ToDo Graph)
2. Redis
3. Gateway (depends on PostgreSQL, Redis)
4. ToDo Graph (depends on PostgreSQL, Redis)
5. Telegram Bot (depends on Gateway, Redis)

### Scaling

**Current Architecture:**
- Single bot instance (Telegram limitation)
- Gateway: Can scale horizontally
- Graphs: Can scale horizontally (multiple instances)
- Redis: Single instance (sessions not critical for scaling)

**Future Scaling:**
- Multiple bot instances with webhook mode + load balancer
- Redis cluster for high availability
- Separate Redis for rate limiting vs sessions

### Maintenance

**Zero-Downtime Update:**
1. Deploy new bot version (new container)
2. Wait for health check
3. Stop old container
4. Redis sessions preserved (if shared)

**Breaking Changes:**
- Clear Redis sessions: `FLUSHDB`
- Notify users to /start again
- Or migrate session schema in deployment script

## Testing Integration

### Manual Testing

1. **Registration Flow:**
   ```bash
   # In Telegram, send /start
   # Check Gateway logs for registration call
   # Check Redis for stored tokens
   ```

2. **Message Routing:**
   ```bash
   # Send message in Telegram
   # Check bot logs for Gateway call
   # Check Gateway logs for graph routing
   # Check ToDo Graph logs for processing
   ```

3. **Agent Switching:**
   ```bash
   # Send /menu, select different agent
   # Send message
   # Verify different session_id in logs
   ```

### Automated Testing

Integration test script (to be implemented):
```bash
#!/bin/bash
# tests/integration/test_bot_to_gateway.sh

# 1. Mock Telegram update (webhook)
# 2. Verify Gateway API call
# 3. Check Redis state
# 4. Verify response format
```

## Future Enhancements

### Webhook Mode

Current: Long polling
Future: Webhook for better scalability

### Multi-Bot Support

Support multiple bot instances with:
- Shared Redis cluster
- Webhook + load balancer
- Distributed rate limiting

### Enhanced Monitoring

- Prometheus metrics export
- Grafana dashboards
- Alert on Gateway connection failures
- Track user engagement metrics

### Additional Frontends

Same architecture pattern for:
- Discord bot
- Web app
- Mobile app
- API clients

All sharing Gateway, but with frontend-specific session management.

