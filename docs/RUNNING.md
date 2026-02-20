# Running Rebot (Current)

This guide matches the current repository implementation.

## 1) Prerequisites

- Python 3.11+
- Flutter SDK (for desktop app)
- Visual Studio Build Tools (Windows Flutter desktop build)
- Optional infra:
  - PostgreSQL (execution persistence)
  - Redis (cross-process event bus)
  - RabbitMQ (external worker queue)

## 2) Backend startup (Desktop recommended: 8001)

From repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Set runtime env (example):

```powershell
$env:REBOT_PORT="8001"
$env:FORCE_LOCAL_TASKS="true"
$env:EMBED_WORKER="true"
# Optional
# $env:DATABASE_URL="postgresql://user:pass@localhost:5432/rebot"
# $env:REDIS_URL="redis://localhost:6379/0"
# $env:RABBITMQ_URL="amqp://guest:guest@localhost:5672/"
```

Start backend:

```powershell
.\.venv\Scripts\python -m app.run_desktop
```

Expected:

- `Starting API on http://0.0.0.0:8001 ...`

## 3) Port conflict check (Windows)

If 8001 is occupied:

```powershell
netstat -ano | findstr :8001
taskkill /PID <PID> /F
```

Then restart backend command above.

## 4) Flutter desktop startup

```powershell
cd desktop\flutter_agentgpt
flutter pub get
flutter run -d windows
```

Build release:

```powershell
flutter build windows
```

## 5) Desktop base URL setting

In Flutter Settings panel, ensure backend base URL is:

- `http://localhost:8001`

## 6) Active API endpoints (current)

### Core run APIs

- `POST /api/execute`
- `POST /api/projects/{project_id}/run`
- `GET /api/run/{id}/stream` (SSE)
- `GET /api/executions/{run_id}`
- `POST /api/executions/{run_id}/cancel`

### System APIs

- `POST /api/devserver/start|stop|status`
- `GET /api/devserver/runtime-baseline`
- `GET /api/emulator/status`
- `POST /api/emulator/start|stop|mirror/start|mirror/stop`
- `POST /api/files/list|read|write`
- `POST /api/generate`
- `POST /api/workflow/execute`

## 7) SSE data flow used by Flutter

`AppState.sendMessage()` now uses standard flow:

- `POST /api/projects/{project_id}/run` -> `run_id`
- `GET /api/run/{id}/stream`

Flutter updates live state on events:

- `stage_update`
- `agent_message`
- `file_generating`
- `file_done`
- `console_log`
- `preview_ready`
- `done`

## 8) Model provider setup notes

- Base URLs are configured in Flutter Settings.
- Endpoint preview in UI shows the effective call target.
- DeepSeek/OpenAI-compatible providers use `/chat/completions` path.

## 9) Optional external worker mode

Use queue-based worker only when needed.

Backend process:

```powershell
$env:FORCE_LOCAL_TASKS="false"
$env:EMBED_WORKER="false"
$env:RABBITMQ_URL="amqp://guest:guest@localhost:5672/"
.\.venv\Scripts\python -m app.main
```

Separate worker process:

```powershell
cd backend
.\.venv\Scripts\activate
.\.venv\Scripts\python -m app.worker
```

## 10) Troubleshooting quick checklist

- 404 on `/devserver/status` or `/emulator/status`:
  - Ensure frontend hits `/api/devserver/status` and `/api/emulator/status`.
- `address already in use` on 8001:
  - Kill existing process on port 8001.
- `Usage: calls=0` and immediate finish:
  - Check provider/base URL/API key/model validity.
- DB connection errors (`psycopg2.OperationalError`):
  - Verify Postgres service/network or run without `DATABASE_URL`.

## 11) Runtime baseline check (production preview readiness)

Check backend runtime dependencies:

```powershell
curl http://localhost:8001/api/devserver/runtime-baseline
```

Expected for full local preview coverage:

- `frameworks.html.ready = true`
- `frameworks.react.ready = true`
- `frameworks.vue.ready = true`
- `frameworks.flutter.ready = true`

## 12) Repository hygiene cleanup (one-time)

If `git status` is polluted by generated/cache files, run:

```powershell
git rm -r --cached --ignore-unmatch backend/.venv
git rm -r --cached --ignore-unmatch desktop/flutter_agentgpt/node_modules
git rm -r --cached --ignore-unmatch backend/.rebot/devserver backend/.rebot/checkpoints backend/.rebot/memory
git rm -r --cached --ignore-unmatch workspace backend/workspace
git add .gitignore backend/.gitignore
git status
```
