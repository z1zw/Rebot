# Architecture (Current Implementation)

This file describes the architecture as implemented in this repository right now.

## 1) Layered design

1. UI Layer
- `desktop/flutter_agentgpt`: primary desktop client
- `frontend`: legacy React workbench

2. API Layer
- `backend/app/api/rest.py`: REST + SSE endpoints
- `backend/app/api/ws.py`: WebSocket event stream endpoint

3. Execution Layer
- `backend/app/worker.py`: worker processing, timeout guard, heartbeat
- `backend/app/core/tasks.py`: local vs Rabbit queue
- `backend/app/core/events.py`: event bus (in-memory/Redis)
- `backend/app/core/executions.py`: run lifecycle persistence + runtime metrics

4. Intelligence Layer
- `rebot/agents`: agent loop + middleware + coding agent + context compression
- `rebot/models`: provider adapters, retry, concurrency and rate limiting
- `rebot/auto`: one-shot generation pipeline + MetaGPT chain/native bridge
- `rebot/workflows`: block graph execution engine
- `rebot/tools`: tool invocation for FS/patch/command

## 2) Main runtime paths

### A) Agent execution path

- Entry: `POST /api/execute`
- Core: `_run_execution` in `backend/app/api/rest.py` (or `backend/app/worker.py`)
- Model provider: `rebot.models.providers.create_chat_model`
- Agent runtime: `CodingAgent.run_task(...)`
- Completion: `ExecutionStore.update(... finished/failed)`

### B) Desktop SSE path

- Entry: `POST /api/projects/{project_id}/run` then `GET /api/run/{id}/stream`
- Backend creates/reuses run, then bridges event bus to SSE frames
- SSE events include:
  - `stage_update`
  - `agent_message`
  - `file_generating`
  - `file_done`
  - `console_log`
  - `preview_ready`
  - `done`

### C) Generation path

- Entry: `POST /api/generate`
- Core: `_run_generate` -> `OneShotGenerator.generate(...)`
- Emits progress via event bus and maps to UI stream

## 3) Concurrency and performance mechanics

Implemented in current code:

- Provider-level concurrency controls (`max_concurrency`, env override)
- Split-task bounded parallelism (`split_task`, `split_max_concurrency`)
- Async boundary protection (`asyncio.to_thread` for sync-heavy operations)
- Token/event streaming back to UI
- Request retry/backoff in model adapter
- Context compression strategies:
  - `summary_stub`
  - `head_tail`
  - `recent_only`
  - `none`

## 4) State and persistence

Run state fields:

- `status`: queued/running/streaming/finalizing/finished/failed/cancelled
- `stage`
- `progress`
- `metrics`
- `result`

Persistence model:

- Primary: SQLModel `Execution` table (if `DATABASE_URL` configured)
- Fallback: in-memory runtime store

## 5) Event transport

- Local default: in-memory queue event bus
- Optional cross-process fanout: Redis pub/sub
- Legacy client channel: WebSocket `/ws/events`
- Desktop live channel: SSE `/api/run/{id}/stream`

## 6) Component responsibilities

### `backend/app/api/rest.py`
- Request schema validation
- Run creation/dedup/cache checks
- Dispatch to local task or queue
- SSE mapping bridge
- Devserver/emulator/files endpoints

### `backend/app/worker.py`
- RabbitMQ consumer pool
- Run dedupe lock (Redis/local)
- Timeout guard and heartbeat
- Worker-side execution for agent/workflow/generate

### `rebot/agents/agent.py`
- Main model-tool loop orchestration
- Middleware hooks (before/after model/tool/agent)
- Structured output parsing strategy
- Context trimming/compression and tool-call routing

### `rebot/models/openai_compatible.py`
- OpenAI-compatible protocol adapter
- Sync/async invoke + stream
- Retry/backoff and rate interval control
- Tool-call sequence sanitization for strict providers

## 7) Known protocol shape (important)

Current desktop standardized flow is:

- `POST /api/projects/{id}/run` + `GET /api/run/{id}/stream`

Compatibility mode still works:

- `GET /api/run/{id}/stream?task=...&api_key=...`

## 8) Directory map (quick)

- `backend/`: service API, worker, infra integrations
- `rebot/`: SDK, agents, models, tools, workflows, generation chain
- `desktop/flutter_agentgpt/`: active desktop app
- `frontend/`: legacy React UI
- `docs/`: documentation
- `scripts/`: local bootstrap and DB init
