# BotsPool Roadmap

## Current Platform Capabilities
- **Core Gateway**: FastAPI service handling JWT auth (RS256), RBAC, graph registry lifecycle, and chat routing across frontends.
- **Telegram Frontend**: Production-ready bot with durable sessions (Postgres + Redis cache), assistant selection, credential escrow, and inline notification handling.
- **ToDo Graph Service**: LangGraph-powered assistant with persistent task CRUD, profiles, and instructions via shared Postgres storage and checkpointer.
- **Notification Service**: API and worker for immediate and scheduled reminders, Telegram delivery, and Redis-backed rate limiting.
- **Shared Utilities**: Central package providing async database layer, migrations, session service, LangGraph helpers, gateway registration, notification tooling, encryption, and documentation.
- **Deployment Tooling**: Docker Compose stacks for infrastructure and each microservice, Alembic migrations, and health endpoints across all components.

## Roadmap

### Stabilization (Q4 2025)
- Implement `/api/v1/subscription/status` and align Telegram messaging for subscription queries.
- Add observability for sessions and notifications (structured logs + metrics for TTL churn, cache hit rate, delivery success).
- Migrate shared models to Pydantic v2 idioms and replace `datetime.utcnow()` usage with timezone-aware alternatives to clear deprecation warnings.
- Expand automated coverage with integration tests for reminder flow and end-to-end smoke suites.

### Feature Expansion (Q1 2026)
- Generalize notification payloads to support additional frontends beyond Telegram.
- Expose public REST/GraphQL endpoints for ToDo management to enable non-Telegram clients.
- Persist conversation transcripts alongside session state for full continuity after redeploys.

### Frontend Diversification (Q2 2026)
- Launch a second frontend (Discord or Web) reusing shared session service and gateway registration.
- Load-test gateway and notification throughput to validate horizontal scaling requirements.

### Platform Hardening (Q3 2026)
- Introduce admin workflows (subscription dashboard, per-frontend configuration management).
- Integrate secrets management for automated JWT key rotation and credential storage.
- Design multi-region deployment strategy with managed Postgres/Redis and failover procedures.
