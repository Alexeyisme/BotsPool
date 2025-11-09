# BotsPool Platform

BotsPool is a multi-service assistant platform that combines LangGraph-powered agent services, a central FastAPI gateway, a notification dispatcher, and production-ready Telegram frontend. The codebase is organised as a mono-repo so individual services can evolve independently while sharing infrastructure and common libraries.

## Repository Layout

- `botspool-gateway/` – FastAPI gateway handling authentication, RBAC, graph registry, and chat routing.
- `botspool-notification-service/` – Notification API and worker for immediate and scheduled reminders.
- `botspool-telegram/` – Telegram bot with durable session persistence and assistant selection UI.
- `botspool-todo-graph/` – LangGraph-based ToDo assistant service with Postgres-backed memory.
- `botspool-shared-utils/` – Shared package providing database utilities, LangGraph helpers, session service, and documentation.
- `docker-compose.infrastructure.yml` – Shared Postgres and Redis stack for local development.
- `ROADMAP.md`, `SECURITY.md`, `NOTIFICATION_SERVICE_IMPLEMENTATION.md` – Cross-service documentation and plans.

## Prerequisites

- Docker 24+
- Docker Compose v2
- Python 3.11 (optional, for running unit tests locally)
- `poetry` or `pip` for installing per-service dev dependencies (optional)

## Quick Start

1. **Provision infrastructure**
   ```bash
   docker compose -f docker-compose.infrastructure.yml up -d
   ```

2. **Apply shared migrations** (requires local Python)
   ```bash
   cd botspool-shared-utils
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/botspool_gateway alembic upgrade head
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/botspool_todograph alembic upgrade head
   ```

3. **Start services** (each directory contains a `docker-compose.yml` for local runs)
   ```bash
   cd botspool-gateway && docker compose up -d --build
   cd ../botspool-notification-service && docker compose up -d --build
   cd ../botspool-todo-graph && docker compose up -d --build
   cd ../botspool-telegram && docker compose up -d --build
   ```

4. **Interact via Telegram** – copy the `.env.example` files for each service (gateway, todo-graph, telegram) and fill in secrets locally before starting containers. Keep the committed versions blank. Once configured, send `/start` to your bot account.

## Testing

- Each service exposes its own `requirements-dev.txt`, `pytest.ini`, and `tests/` directory.
- Shared utilities include unit and integration suites runnable via `pytest`.
- Consider using service-specific virtual environments (ignored from version control).

## Deployment Notes

- Sample environment files: see `env.example` or `env.docker.example` within each service.
- Dockerfiles are production ready; Compose files target local orchestration for reproducible builds.
- Redis caching for sessions is enabled by default in production; configure via `SESSION_` environment variables.

## Additional Documentation

- `botspool-shared-utils/docs/` – Detailed architecture, API reference, migrations, and security policies.
- `BOTPOOL/ROADMAP.md` – Platform roadmap and future milestones.
- `NOTIFICATION_SERVICE_IMPLEMENTATION.md` – Full design notes for notification subsystem.
- `TELEGRAM_BOT_FINAL_REPORT.md` – Summary of Telegram integration milestones.

## Preparing for GitHub

- `.gitignore` excludes development environments, caches, and generated files.
- Secrets and `.env` files are intentionally omitted; provide sample templates instead.
- Before publishing, run a full test suite and lint pass per service as needed.
