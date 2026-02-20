# Deployment (Current Notes)

## 1) Local infra via Docker Compose

Repository includes `docker-compose.yml` for local dependencies and backend containerized run.

Typical stack:

- Postgres
- Redis
- RabbitMQ
- Backend

> Note: Desktop local workflow usually runs backend directly on `8001` via `python -m app.run_desktop`.
> Compose examples often map backend to `8000`; adjust as needed for your environment.

## 2) Recommended desktop deployment mode

For desktop app users, prefer:

1. Start backend locally on `8001`
2. Run Flutter desktop app
3. Set backend base URL to `http://localhost:8001`

This avoids mismatch with legacy `8000` assumptions.

## 3) Production separation

Run API and worker as separate processes:

- API: `python -m app.main`
- Worker: `python -m app.worker`

Required env in production:

- `DATABASE_URL`
- `REDIS_URL` (recommended)
- `RABBITMQ_URL` (for external queue mode)

Optional:

- `SENTRY_DSN`
- `SUPABASE_*`
- `CLAMAV_*`

## 4) Database init

Use scripts based on your need:

- `scripts/init_db.sql`
- `scripts/init_pgvector.sql`
- `scripts/init_all.sql`

## 5) Desktop clients

### Flutter desktop (primary)

- Directory: `desktop/flutter_agentgpt`
- Uses backend REST/SSE endpoints directly

### Electron (legacy)

- Directory: `desktop/electron`
- Kept for compatibility/legacy workflows

## 6) Endpoint compatibility reminder

Current live streaming endpoint in use:

- `GET /api/run/{id}/stream`

If introducing run-id style stream APIs later, keep backward compatibility for existing desktop clients.
