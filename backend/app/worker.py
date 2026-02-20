from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Protocol

import aio_pika

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rebot import ModelConfig, CodingAgent
from rebot.models.providers import create_chat_model
from rebot.core.trace import TraceCollector
from rebot.core.messages import Message
from rebot.workflows import (
    WorkflowSpec,
    WorkflowExecutor,
    ExecutionContext,
    create_default_registry,
)
from rebot.tools.fs_tools import (
    ListFilesTool,
    ReadFileTool,
    WriteFileTool,
    ReplaceInFileTool,
    ApplyPatchTool,
)
from rebot.tools.command_tool import RunTestsTool
from app.core.events import get_event_bus
from app.intel.repo_map import RepoMapBuilder
from app.intel.ast_index import ASTCodeIndexer
from app.intel.experience_memory import ExperienceMemory
from app.intel.failure_memory import FailureMemory
from app.orchestration.multi_agent_scheduler import MultiAgentScheduler
from app.core.smoke_gate import run_framework_smoke_check
from app.core.smoke_rework import build_smoke_rework_task, detect_environment_blockers
from app.core.llm_routing import normalize_llm_selection
from app.core.executions import (
    ExecutionStore,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_STREAMING,
    STATUS_FINALIZING,
    STATUS_FINISHED,
    STATUS_FAILED,
    STATUS_CANCELLED,
)
from app.core.settings import settings


def _is_game_task(task: str) -> bool:
    text = (task or "").strip().lower()
    if not text:
        return False
    keywords = (
        "game",
        "小游戏",
        "游戏",
        "arcade",
        "maze",
        "platformer",
        "shooter",
        "runner",
        "puzzle",
    )
    return any(k in text for k in keywords)


def _augment_game_task_for_production(task: str) -> str:
    base = (task or "").strip()
    contract = (
        "PRODUCTION_GAME_CONTRACT\n"
        "- Build a polished, visually strong, interactive web game (not static document).\n"
        "- Use canvas or DOM game loop with clear state transitions: idle/running/paused/win/lose.\n"
        "- Keep all DOM ids consistent between HTML and JS. Never reference missing ids.\n"
        "- Include responsive layout, modern styling, readable typography, and clear controls.\n"
        "- Define explicit visual tokens (color/spacing/radius/shadow/typography), not browser defaults.\n"
        "- Use multi-tab/segmented UI sections (e.g., Play/Guide/Stats/Settings) for production information architecture.\n"
        "- Avoid plain white background; use layered gradients or rich surfaces with clear hierarchy.\n"
        "- Ensure buttons/cards/hud have polished states (hover/active/disabled) and cohesive palette.\n"
        "- Provide complete runnable files with no placeholders and no pseudo-code.\n"
        "- Validate runtime wiring before returning: controls work, score/life/time update, restart works.\n"
    )
    if "PRODUCTION_GAME_CONTRACT" in base:
        return base
    return f"{base}\n\n{contract}"


@dataclass
class RunDeduper:
    redis_url: str | None
    _local_running: set[str] = field(default_factory=set)
    _local_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def acquire(self, run_id: str, ttl_s: int = 3600) -> bool:
        if self.redis_url:
            try:
                import redis.asyncio as redis

                client = redis.from_url(self.redis_url, decode_responses=True)
                key = f"rebot:runlock:{run_id}"
                ok = await client.set(key, "1", ex=ttl_s, nx=True)
                return bool(ok)
            except Exception:
                pass
        async with self._local_lock:
            if run_id in self._local_running:
                return False
            self._local_running.add(run_id)
            return True

    async def release(self, run_id: str) -> None:
        if self.redis_url:
            try:
                import redis.asyncio as redis

                client = redis.from_url(self.redis_url, decode_responses=True)
                await client.delete(f"rebot:runlock:{run_id}")
            except Exception:
                pass
        async with self._local_lock:
            self._local_running.discard(run_id)


class ExecutionBackend(Protocol):
    async def run_agent(self, run_id: str, data: dict[str, object]) -> None: ...
    async def run_workflow(self, run_id: str, data: dict[str, object]) -> None: ...
    async def run_generate(self, run_id: str, data: dict[str, object]) -> None: ...


class LegacyLocalBackend:
    async def run_agent(self, run_id: str, data: dict[str, object]) -> None:
        await _run_execution(run_id, data)

    async def run_workflow(self, run_id: str, data: dict[str, object]) -> None:
        await _run_workflow_execution(run_id, data)

    async def run_generate(self, run_id: str, data: dict[str, object]) -> None:
        await _run_generate(run_id, data)


class DockerBackend:
    """
    Adapter placeholder for V2 runtime.
    This is intentionally additive: legacy path remains default and unchanged.
    """

    async def run_agent(self, run_id: str, data: dict[str, object]) -> None:
        await self._run_v2(run_id, data, job_type="agent")

    async def run_workflow(self, run_id: str, data: dict[str, object]) -> None:
        await self._run_v2(run_id, data, job_type="workflow")

    async def run_generate(self, run_id: str, data: dict[str, object]) -> None:
        await self._run_v2(run_id, data, job_type="generate")

    async def _run_v2(self, run_id: str, data: dict[str, object], *, job_type: str) -> None:
        """
        Expected runtime module contract (additive module):
        backend/app/runtime/docker_sandbox.py
          - class DockerSessionManager
          - async method: execute_job(run_id=..., payload=..., job_type=...)
        """
        try:
            from app.runtime.docker_sandbox import DockerSessionManager  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "Docker runtime module is not available. "
                "Create backend/app/runtime/docker_sandbox.py with DockerSessionManager."
            ) from exc

        manager = DockerSessionManager()
        execute_job = getattr(manager, "execute_job", None)
        if execute_job is None:
            raise RuntimeError(
                "DockerSessionManager.execute_job is missing. "
                "Please implement execute_job(run_id, payload, job_type)."
            )
        result = execute_job(run_id=run_id, payload=data, job_type=job_type)
        if asyncio.iscoroutine(result):
            await result


_LEGACY_BACKEND: ExecutionBackend = LegacyLocalBackend()
_DOCKER_BACKEND: ExecutionBackend = DockerBackend()


def _resolve_execution_mode(data: dict[str, object]) -> str:
    """
    Modes:
      - legacy_local (default, no regression)
      - docker_v2
    Selection order:
      1) payload.execution_mode
      2) env REBOT_EXECUTION_MODE
      3) auto heuristic
    """
    payload_mode = str(data.get("execution_mode") or "").strip().lower()
    if payload_mode in {"legacy", "local", "legacy_local", "lite"}:
        return "legacy_local"
    if payload_mode in {"docker", "docker_v2", "v2"}:
        return "docker_v2"

    env_mode = os.getenv("REBOT_EXECUTION_MODE", "auto").strip().lower()
    if env_mode in {"legacy", "local", "legacy_local", "lite"}:
        return "legacy_local"
    if env_mode in {"docker", "docker_v2", "v2"}:
        return "docker_v2"

    # auto: choose docker only when explicitly requested by payload hints.
    if bool(data.get("docker_enabled")) or data.get("docker_image") is not None:
        return "docker_v2"
    return "legacy_local"


def _docker_fallback_enabled() -> bool:
    return os.getenv("REBOT_DOCKER_FALLBACK", "true").strip().lower() in {"1", "true", "yes", "on"}


def _as_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _backend_for_mode(mode: str) -> ExecutionBackend:
    return _DOCKER_BACKEND if mode == "docker_v2" else _LEGACY_BACKEND


async def _dispatch_run_by_mode(run_id: str, data: dict[str, object]) -> None:
    bus = get_event_bus()
    mode = _resolve_execution_mode(data)
    job_type = str(data.get("job_type") or "agent")
    ExecutionStore.update(
        run_id,
        metrics={
            "job_type": job_type,
            "execution_mode": mode,
        },
    )

    backend = _backend_for_mode(mode)

    async def _run_with_backend(b: ExecutionBackend) -> None:
        if job_type == "workflow":
            await b.run_workflow(run_id, data)
        elif job_type == "generate":
            await b.run_generate(run_id, data)
        else:
            await b.run_agent(run_id, data)

    try:
        await _run_with_backend(backend)
    except Exception as exc:
        if mode == "docker_v2" and _docker_fallback_enabled():
            await bus.publish_event(
                run_id,
                {
                    "type": "run_progress",
                    "payload": f"[runtime] docker_v2 failed, fallback to legacy_local: {exc}",
                },
            )
            ExecutionStore.update(
                run_id,
                metrics={
                    "job_type": job_type,
                    "execution_mode": "legacy_local",
                    "runtime_fallback": "docker_v2->legacy_local",
                },
            )
            await _run_with_backend(_LEGACY_BACKEND)
            return
        raise


async def run_worker() -> None:
    if not settings.rabbitmq_url:
        print("Worker: RABBITMQ_URL is empty. Exiting.")
        return
    print(f"Worker: database_url={'set' if settings.database_url else 'missing'}")
    print(f"Worker: redis_url={'set' if settings.redis_url else 'missing'}")
    print("Worker: connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    deduper = RunDeduper(settings.redis_url)
    async with connection:
        concurrency = int(os.getenv("WORKER_CONCURRENCY", "2"))
        print(f"Worker: connected. Starting {concurrency} consumers on rebot.tasks...")

        async def consume_one(worker_id: int) -> None:
            channel = await connection.channel()
            queue = await channel.declare_queue("rebot.tasks", durable=True)
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        payload = json.loads(message.body.decode("utf-8"))
                        run_id = payload["run_id"]
                        print(f"Worker[{worker_id}]: received task {run_id}")
                        existing = ExecutionStore.get(run_id)
                        if existing is not None and existing.status in {
                            STATUS_RUNNING,
                            STATUS_STREAMING,
                            STATUS_FINALIZING,
                            STATUS_FINISHED,
                            STATUS_FAILED,
                            STATUS_CANCELLED,
                        }:
                            print(
                                f"Worker[{worker_id}]: skip run_id={run_id} status={existing.status}"
                            )
                            continue
                        acquired = await deduper.acquire(run_id)
                        if not acquired:
                            print(f"Worker[{worker_id}]: duplicate task skipped {run_id}")
                            continue
                        data = payload["payload"]
                        try:
                            job_type = str(data.get("job_type") or "agent")
                            mode = _resolve_execution_mode(data)
                            ExecutionStore.update(
                                run_id,
                                status=STATUS_RUNNING,
                                stage="running",
                                progress=f"Worker[{worker_id}] started.",
                                metrics={"worker_id": worker_id, "job_type": job_type, "execution_mode": mode},
                            )
                            print(
                                f"Worker[{worker_id}]: processing {run_id} "
                                f"job_type={job_type} mode={mode}"
                            )
                            timeout_s = int(os.getenv("REBOT_TASK_TIMEOUT_S", "1800"))
                            await _run_with_guard(
                                run_id,
                                _dispatch_run_by_mode(run_id, data),
                                timeout_s=timeout_s,
                            )
                        except Exception as exc:
                            print(f"Worker[{worker_id}]: task failed {run_id}: {exc}")
                            traceback.print_exc()
                            ExecutionStore.update(
                                run_id,
                                status=STATUS_FAILED,
                                stage="failed",
                                progress=str(exc),
                                result={
                                    "error": str(exc),
                                    "job_type": str(data.get("job_type") or "agent"),
                                    "code": "E_WORKER_FAILED",
                                },
                            )
                            bus = get_event_bus()
                            await bus.publish_event(
                                run_id,
                                {"type": "run_error", "payload": {"error": str(exc), "code": "E_WORKER_FAILED"}},
                            )
                        finally:
                            await deduper.release(run_id)

        await asyncio.gather(*(consume_one(i + 1) for i in range(concurrency)))


async def _run_with_guard(run_id: str, coro: asyncio.Future | Any, *, timeout_s: int) -> None:
    bus = get_event_bus()
    stop_heartbeat = False

    async def heartbeat() -> None:
        while not stop_heartbeat:
            await asyncio.sleep(5)
            if stop_heartbeat:
                break
            rec = ExecutionStore.get(run_id)
            if rec is None:
                continue
            if rec.status == STATUS_CANCELLED:
                break
            ExecutionStore.update(
                run_id,
                metrics={"heartbeat_ts": time.time()},
            )
            await bus.publish_event(
                run_id,
                {"type": "run_heartbeat", "payload": {"ts": time.time(), "stage": rec.stage}},
            )

    hb = asyncio.create_task(heartbeat())
    try:
        rec = ExecutionStore.get(run_id)
        if rec is not None and rec.status == STATUS_CANCELLED:
            raise RuntimeError("Run cancelled before execution.")
        await asyncio.wait_for(coro, timeout=float(timeout_s))
    except asyncio.TimeoutError as exc:
        ExecutionStore.update(
            run_id,
            status=STATUS_FAILED,
            stage="failed",
            progress=f"Task timeout after {timeout_s}s.",
            result={"error": f"Task timeout after {timeout_s}s.", "code": "E_TIMEOUT"},
        )
        await bus.publish_event(
            run_id,
            {"type": "run_error", "payload": {"error": f"Task timeout after {timeout_s}s.", "code": "E_TIMEOUT"}},
        )
        raise RuntimeError("Task timed out") from exc
    finally:
        stop_heartbeat = True
        hb.cancel()


async def _run_execution(run_id: str, data: dict[str, object]) -> None:
    if _use_worker_multi_agent(data):
        await _run_execution_multi_agent(run_id, data)
        return

    provider_norm, base_url_norm = normalize_llm_selection(
        provider=(str(data["provider"]) if data.get("provider") is not None else None),
        model=str(data["model"]),
        base_url=str(data["base_url"]),
    )
    data["provider"] = provider_norm
    data["base_url"] = base_url_norm

    ExecutionStore.update(run_id, status=STATUS_RUNNING, stage="agent", progress="Running coding agent...")
    model_max_concurrency = _resolve_model_max_concurrency(
        requested=(
            int(data["model_max_concurrency"])
            if data.get("model_max_concurrency") is not None
            else None
        ),
        model=str(data["model"]),
        base_url=str(data["base_url"]),
    )
    model = create_chat_model(
        ModelConfig(
            api_key=str(data["api_key"]),
            model=str(data["model"]),
            base_url=str(data["base_url"]),
            max_concurrency=model_max_concurrency,
        ),
        provider=(str(data["provider"]) if data.get("provider") is not None else None),
    )
    agent = CodingAgent(
        model=model, workspace_root=Path(str(data["workspace"])), review_mode=bool(data["review_mode"])
    )
    events: list[dict] = []
    bus = get_event_bus()
    native_metrics: dict[str, Any] = {}
    loop = asyncio.get_running_loop()

    def _publish_event_threadsafe(event: dict[str, object]) -> None:
        try:
            asyncio.run_coroutine_threadsafe(bus.publish_event(run_id, event), loop)
        except Exception:
            pass

    def stream_cb(chunk):
        ExecutionStore.update(run_id, status=STATUS_STREAMING, stage="streaming", progress="Streaming model output...")
        _publish_event_threadsafe({"type": "token", "payload": chunk.content})

    def sink(event: dict[str, object]) -> None:
        _publish_event_threadsafe(event)

    callbacks = TraceCollector(run_id=run_id, sink=sink, events=events)

    if data.get("metagpt_native"):
        await bus.publish_event(
            run_id,
            {"type": "run_stage", "payload": {"stage": "metagpt_native", "message": "Running native MetaGPT..."}},
        )
        try:
            from rebot.auto.metagpt_native_bridge import run_native_metagpt

            native = await asyncio.to_thread(
                run_native_metagpt,
                requirement=str(data["task"]),
                workspace=str(data["workspace"]),
                api_key=str(data["api_key"]),
                model=str(data["model"]),
                base_url=str(data["base_url"]),
                repo_path=(
                    str(data["metagpt_native_repo"])
                    if data.get("metagpt_native_repo") is not None
                    else None
                ),
                rounds=int(data.get("metagpt_native_rounds", 5)),
                investment=float(data.get("metagpt_native_investment", 3.0)),
            )
            native_metrics = {
                "metagpt_native_history": int(native.history_size),
                "metagpt_native_cost": float(native.total_cost),
                "metagpt_native_rounds": int(native.rounds),
                "metagpt_native_enabled": 1,
            }
            ExecutionStore.update(run_id, metrics=dict(native_metrics))
            await bus.publish_event(
                run_id,
                {
                    "type": "run_progress",
                    "payload": (
                        f"MetaGPT native done: history={native.history_size}, cost={native.total_cost:.4f}"
                    ),
                },
            )
            if data.get("metagpt_native_only"):
                result = {
                    "report": (
                        f"MetaGPT native completed.\n"
                        f"history={native.history_size}, cost={native.total_cost:.4f}, rounds={native.rounds}"
                    ),
                    "graph": "",
                }
                from app.core.cache import cache

                cache_key = str(
                    data.get("cache_key")
                    or (
                        f"{data.get('provider')}:{data['model']}:{data['base_url']}:{data['task']}:"
                        f"{data['workspace']}:{data.get('review_mode')}:"
                        f"{data.get('dialog_mode')}:{data.get('attention')}:"
                        f"{data.get('context_compress_type')}:{data.get('context_head_ratio')}:"
                        f"{data.get('max_context_tokens')}:"
                        f"{data.get('metagpt_native')}:{data.get('metagpt_native_repo')}:"
                        f"{data.get('metagpt_native_rounds')}:{data.get('metagpt_native_investment')}:"
                        f"{data.get('metagpt_native_only')}"
                    )
                )
                cache.set(cache_key, result, ttl_s=data.get("cache_ttl_s"))
                ExecutionStore.update(
                    run_id,
                    status=STATUS_FINISHED,
                    stage="done",
                    progress="Completed.",
                    result=result,
                    metrics=dict(native_metrics),
                )
                return
        except Exception as exc:
            await bus.publish_event(
                run_id,
                {"type": "run_progress", "payload": f"MetaGPT native fallback: {exc}"},
            )

    configurable = {
        "max_context_chars": data.get("max_context_chars") or 32000,
        "max_context_tokens": (
            int(data["max_context_tokens"])
            if data.get("max_context_tokens") is not None
            else None
        ),
        "context_compress_type": data.get("context_compress_type") or "summary_stub",
        "context_head_ratio": (
            float(data["context_head_ratio"])
            if data.get("context_head_ratio") is not None
            else 0.25
        ),
        "context_matrix_rows": (
            int(data["context_matrix_rows"])
            if data.get("context_matrix_rows") is not None
            else 8
        ),
        "context_matrix_cols": (
            int(data["context_matrix_cols"])
            if data.get("context_matrix_cols") is not None
            else 8
        ),
        "context_sketch_dim": (
            int(data["context_sketch_dim"])
            if data.get("context_sketch_dim") is not None
            else 64
        ),
        "tool_max_workers": data.get("tool_max_workers"),
    }
    from app.core.task_split import split_task

    tasks = (
        split_task(str(data["task"]), int(data.get("split_chunk_chars", 800)))
        if data.get("split_task")
        else [str(data["task"])]
    )
    reports: list[str] = []
    usage_totals = {"model_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    usage_lock = asyncio.Lock()
    split_max_concurrency = _resolve_split_max_concurrency(
        int(data["split_max_concurrency"])
        if data.get("split_max_concurrency") is not None
        else None,
        len(tasks),
        default_limit=max(1, min(3, model_max_concurrency)),
    )
    async def run_chunk(idx: int, task: str) -> str:
        await bus.publish_event(run_id, {"type": "chunk_start", "payload": idx})
        state = await asyncio.to_thread(
            agent.run_task,
            task,
            events=events,
            callbacks=callbacks,
            stream_callback=stream_cb,
            dialog_mode=(
                str(data["dialog_mode"])
                if data.get("dialog_mode") is not None
                else None
            ),
            attention=(
                float(data["attention"])
                if data.get("attention") is not None
                else None
            ),
            configurable=configurable,
        )
        chunk_usage = _extract_usage_metrics(state.messages)
        async with usage_lock:
            for k in usage_totals:
                usage_totals[k] += int(chunk_usage.get(k, 0))
            ExecutionStore.update(run_id, metrics=dict(usage_totals))
        from app.core.schemas import ChunkResult

        payload = ChunkResult(index=idx, report=state.report, changes=state.change_log).model_dump()
        await bus.publish_event(run_id, {"type": "chunk_end", "payload": payload})
        return state.report or ""

    if data.get("split_task") and len(tasks) > 1:
        await bus.publish_event(
            run_id,
            {
                "type": "run_progress",
                "payload": (
                    f"Split into {len(tasks)} chunks, "
                    f"max concurrency={split_max_concurrency}."
                ),
            },
        )
        reports = await _run_chunks_limited(tasks, run_chunk, split_max_concurrency)
    else:
        reports = [await run_chunk(0, tasks[0])]
    await bus.publish(run_id, events)
    result = {"report": "\n\n".join(reports), "graph": ""}
    from app.core.cache import cache

    cache_key = str(
        data.get("cache_key")
        or (
            f"{data.get('provider')}:{data['model']}:{data['base_url']}:{data['task']}:"
            f"{data['workspace']}:{data.get('review_mode')}:"
            f"{data.get('dialog_mode')}:{data.get('attention')}:"
            f"{data.get('context_compress_type')}:{data.get('context_head_ratio')}:"
            f"{data.get('max_context_tokens')}:"
            f"{data.get('metagpt_native')}:{data.get('metagpt_native_repo')}:"
            f"{data.get('metagpt_native_rounds')}:{data.get('metagpt_native_investment')}:"
            f"{data.get('metagpt_native_only')}"
        )
    )
    cache.set(cache_key, result, ttl_s=data.get("cache_ttl_s"))
    ExecutionStore.update(
        run_id,
        status=STATUS_FINISHED,
        stage="done",
        progress="Completed.",
        result=result,
        metrics={**native_metrics, **dict(usage_totals)},
    )


def _use_worker_multi_agent(data: dict[str, object]) -> bool:
    explicit = data.get("multi_agent")
    if explicit is not None:
        return _as_bool(explicit, False)
    env_default = os.getenv("REBOT_WORKER_MULTI_AGENT_DEFAULT", "false").strip().lower()
    return env_default in {"1", "true", "yes", "on"}


def _safe_join_workspace_worker(workspace_root: Path, rel_path: str) -> Path:
    clean = (rel_path or "").replace("\\", "/").lstrip("/")
    target = (workspace_root / clean).resolve()
    root = workspace_root.resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Path escapes workspace: {rel_path}")
    return target


async def _run_execution_multi_agent(run_id: str, data: dict[str, object]) -> None:
    provider_norm, base_url_norm = normalize_llm_selection(
        provider=(str(data["provider"]) if data.get("provider") is not None else None),
        model=str(data["model"]),
        base_url=str(data["base_url"]),
    )
    data["provider"] = provider_norm
    data["base_url"] = base_url_norm

    ExecutionStore.update(run_id, status=STATUS_RUNNING, stage="planner", progress="Running multi-agent scheduler...")
    bus = get_event_bus()
    workspace_root = Path(str(data["workspace"]))
    workspace_root.mkdir(parents=True, exist_ok=True)
    checkpoint_enabled = _as_bool(data.get("checkpoint_enabled"), True)
    checkpoint_path = str(workspace_root / ".rebot" / "checkpoints" / f"{run_id}.json")
    ExecutionStore.update(
        run_id,
        metrics={
            "checkpoint_enabled": 1 if checkpoint_enabled else 0,
            "checkpoint_path": checkpoint_path,
        },
    )

    model_max_concurrency = _resolve_model_max_concurrency(
        requested=(
            int(data["model_max_concurrency"])
            if data.get("model_max_concurrency") is not None
            else None
        ),
        model=str(data["model"]),
        base_url=str(data["base_url"]),
    )
    model = create_chat_model(
        ModelConfig(
            api_key=str(data["api_key"]),
            model=str(data["model"]),
            base_url=str(data["base_url"]),
            max_concurrency=model_max_concurrency,
        ),
        provider=(str(data["provider"]) if data.get("provider") is not None else None),
    )

    loop = asyncio.get_running_loop()

    def _publish_event_threadsafe_ma(event: dict[str, object]) -> None:
        try:
            asyncio.run_coroutine_threadsafe(bus.publish_event(run_id, event), loop)
        except Exception:
            pass

    async def _emit(event_type: str, payload: object) -> None:
        try:
            if event_type == "run_stage" and isinstance(payload, dict):
                st = str(payload.get("stage") or "").strip()
                msg = str(payload.get("message") or "").strip()
                if st:
                    ExecutionStore.update(run_id, stage=st, progress=msg or f"Stage: {st}")
            elif event_type == "run_progress":
                msg = str(payload or "").strip()
                if msg:
                    rec = ExecutionStore.get(run_id)
                    ExecutionStore.update(run_id, stage=(rec.stage if rec else "running"), progress=msg)
        except Exception:
            pass
        try:
            await asyncio.wait_for(
                bus.publish_event(run_id, {"type": event_type, "payload": payload}),
                timeout=float(os.getenv("REBOT_EVENT_EMIT_TIMEOUT_S", "2.5")),
            )
        except Exception:
            return

    async def _llm_call(system_prompt: str, user_prompt: str) -> str:
        """LLM call with streaming token emission for multi-agent workflow."""
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]
        collected_content: list[str] = []

        def _stream_cb(chunk: Message) -> None:
            """Emit each token as it arrives for real-time UI feedback."""
            content = getattr(chunk, "content", "") or ""
            if content:
                collected_content.append(content)
                _publish_event_threadsafe_ma({"type": "token", "payload": content})

        def _invoke_with_stream() -> Message:
            return model.invoke(messages, tools=[], stream_callback=_stream_cb)

        rsp = await asyncio.to_thread(_invoke_with_stream)
        # Use collected content if streaming worked, else fall back to response content
        if collected_content:
            return "".join(collected_content).strip()
        return str(getattr(rsp, "content", "") or "").strip()

    def _resolve_role_model(role: str):
        overrides = data.get("role_model_overrides")
        role_cfg = None
        if isinstance(overrides, dict):
            candidate = overrides.get(role)
            if isinstance(candidate, dict):
                role_cfg = candidate
        if role_cfg is None:
            return (
                (str(data["provider"]) if data.get("provider") is not None else None),
                str(data["model"]),
                str(data["base_url"]),
                str(data["api_key"]),
                model_max_concurrency,
            )
        provider = str(role_cfg.get("provider") or data.get("provider") or "").strip()
        model_name = str(role_cfg.get("model") or data["model"]).strip()
        base_url = str(role_cfg.get("base_url") or data["base_url"]).strip()
        provider, base_url = normalize_llm_selection(
            provider=provider if provider else None,
            model=model_name,
            base_url=base_url,
        )
        api_key = str(role_cfg.get("api_key") or data["api_key"]).strip()
        try:
            max_c = max(1, int(role_cfg.get("max_concurrency"))) if role_cfg.get("max_concurrency") is not None else model_max_concurrency
        except Exception:
            max_c = model_max_concurrency
        return (provider if provider else None, model_name, base_url, api_key, max_c)

    async def _role_llm_call(role: str, system_prompt: str, user_prompt: str) -> str:
        provider, model_name, base_url, api_key, max_c = _resolve_role_model(role)
        role_model = create_chat_model(
            ModelConfig(
                api_key=api_key,
                model=model_name,
                base_url=base_url,
                max_concurrency=max_c,
            ),
            provider=provider,
        )
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]
        collected_content: list[str] = []

        def _stream_cb(chunk: Message) -> None:
            content = getattr(chunk, "content", "") or ""
            if content:
                collected_content.append(content)
                _publish_event_threadsafe_ma({"type": "token", "payload": content})

        def _invoke_with_stream() -> Message:
            return role_model.invoke(messages, tools=[], stream_callback=_stream_cb)

        rsp = await asyncio.to_thread(_invoke_with_stream)
        if collected_content:
            return "".join(collected_content).strip()
        return str(getattr(rsp, "content", "") or "").strip()

    cache_key = str(
        data.get("cache_key")
        or (
            f"{data.get('provider')}:{data['model']}:{data['base_url']}:{data.get('task')}:{data['workspace']}:"
            f"multi_agent:{data.get('multi_agent')}:repo_map:{data.get('repo_map')}:exp:{data.get('experience_memory')}"
        )
    )

    retry_budget = int(data.get("retry_budget") or os.getenv("REBOT_MULTI_AGENT_RETRY_BUDGET", "2"))
    if retry_budget < 0:
        retry_budget = 0
    max_workers = int(data.get("multi_agent_workers") or model_max_concurrency)
    if max_workers < 1:
        max_workers = 1

    use_repo_map = _as_bool(data.get("repo_map"), True)
    use_ast_context = _as_bool(
        data.get("ast_context"),
        os.getenv("REBOT_AST_CONTEXT_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"},
    )
    use_memory = _as_bool(data.get("experience_memory"), True)
    smoke_check_enabled = _as_bool(data.get("smoke_check_enabled"), True)
    smoke_rework_budget = int(data.get("smoke_rework_budget") or 1)
    if smoke_rework_budget < 0:
        smoke_rework_budget = 0
    if smoke_rework_budget > 3:
        smoke_rework_budget = 3

    repo_map_text = ""
    if use_repo_map:
        builder = RepoMapBuilder(workspace_root)
        repo_map = builder.build()
        repo_map_text = builder.to_compact_text(repo_map)
        await _emit("run_progress", f"RepoMap ready: files={repo_map.get('file_count', 0)}")

    ast_context_text = ""
    if use_ast_context:
        try:
            ast_indexer = ASTCodeIndexer(workspace_root, max_files=300, max_file_bytes=512_000)
            ast_index = ast_indexer.build(include_references=True)
            ast_context_text = ast_indexer.to_compact_text(ast_index, max_chars=12000)
            await _emit(
                "run_progress",
                f"AST context ready: files={ast_index.get('file_count', 0)}, symbols={ast_index.get('symbol_count', 0)}",
            )
        except Exception as exc:
            await _emit("console_log", {"text": f"[ast_context] build failed: {exc}", "level": "warning"})

    memory_hits: list[str] = []
    memory: ExperienceMemory | None = None
    failure_memory = FailureMemory(workspace_root / ".rebot" / "memory")
    if use_memory:
        memory_timeout_s = max(3.0, float(os.getenv("REBOT_MEMORY_QUERY_TIMEOUT_S", "12")))
        try:
            def _init_and_query_memory() -> tuple[ExperienceMemory, list[str]]:
                m = ExperienceMemory(workspace_root / ".rebot" / "memory")
                hits = m.query(str(data.get("task") or ""), top_k=4)
                return m, hits

            memory, memory_hits = await asyncio.wait_for(
                asyncio.to_thread(_init_and_query_memory),
                timeout=memory_timeout_s,
            )
            await _emit("run_progress", f"ExperienceMemory backend={memory.mode}, hits={len(memory_hits)}")
        except asyncio.TimeoutError:
            memory = None
            memory_hits = []
            await _emit("console_log", {"text": f"[memory] query timeout>{int(memory_timeout_s)}s, degraded to no-memory mode", "level": "warning"})
        except Exception as exc:
            memory = None
            memory_hits = []
            await _emit("console_log", {"text": f"[memory] unavailable: {exc}", "level": "warning"})
    try:
        playbook_hits = failure_memory.query(
            query=str(data.get("task") or ""),
            framework=str(data.get("framework") or ""),
            top_k=3,
        )
    except Exception:
        playbook_hits = []
    if playbook_hits:
        memory_hits.extend(playbook_hits)
        await _emit("console_log", {"text": f"[failure_playbook] loaded {len(playbook_hits)} hint(s)", "level": "info"})

    resume_checkpoint: dict[str, object] | None = None
    resume_from = str(data.get("resume_from_run_id") or "").strip()
    if resume_from:
        src = ExecutionStore.get(resume_from)
        src_path = ""
        if src is not None:
            src_path = str(src.metrics.get("checkpoint_path") or "").strip()
        if src_path:
            cp = Path(src_path)
            if cp.exists():
                try:
                    loaded = json.loads(cp.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        stage_override = str(data.get("resume_checkpoint_stage") or "").strip()
                        if stage_override:
                            loaded["stage"] = stage_override
                        resume_checkpoint = loaded
                        await _emit(
                            "console_log",
                            {
                                "text": f"[checkpoint] worker resume from {resume_from} stage={loaded.get('stage')}",
                                "level": "info",
                            },
                        )
                except Exception as exc:
                    await _emit("console_log", {"text": f"[checkpoint] worker resume load failed: {exc}", "level": "warning"})

    scheduler = MultiAgentScheduler(
        llm_call=_llm_call,
        role_llm_call=_role_llm_call,
        emit=_emit,
        max_workers=max_workers,
        retries=2,
        max_token_budget=(
            int(data["max_token_budget"]) if data.get("max_token_budget") is not None else None
        ),
        max_cost_budget=(
            float(data["max_cost_budget"]) if data.get("max_cost_budget") is not None else None
        ),
        checkpoint_dir=(
            (workspace_root / ".rebot" / "checkpoints")
            if checkpoint_enabled
            else None
        ),
        run_id=run_id,
    )

    attempt = 0
    plan_result: dict[str, object] = {}
    generated_paths: list[str] = []
    base_task = str(data.get("task") or "")
    scheduler_framework = str(data.get("framework") or "") if data.get("framework") else None
    task_for_generation = base_task
    if (scheduler_framework or "").strip().lower() in {"", "general"} and _is_game_task(base_task):
        task_for_generation = _augment_game_task_for_production(base_task)
        scheduler_framework = "html"
        await _emit("console_log", {"text": "[task_policy] general+game detected, forcing html production game contract", "level": "info"})

    while True:
        backups: dict[Path, tuple[bool, str]] = {}
        touched: list[Path] = []
        try:
            attempt += 1
            ExecutionStore.update(run_id, stage="planner", progress=f"Multi-agent planning attempt {attempt}...")
            if resume_checkpoint is not None:
                plan_result = await scheduler.run_from_checkpoint(
                    task=task_for_generation,
                    repo_map=repo_map_text,
                    ast_context=ast_context_text,
                    memory_hints=memory_hits,
                    checkpoint=resume_checkpoint,
                    framework=scheduler_framework,
                )
            else:
                plan_result = await scheduler.run(
                    task=task_for_generation,
                    repo_map=repo_map_text,
                    ast_context=ast_context_text,
                    memory_hints=memory_hits,
                    framework=scheduler_framework,
                )

            ExecutionStore.update(run_id, stage="implement", progress="Applying generated artifacts...")
            artifacts = plan_result.get("artifacts") if isinstance(plan_result, dict) else None
            if not isinstance(artifacts, list):
                artifacts = []
            generated_paths = []

            for item in artifacts:
                if not isinstance(item, dict):
                    continue
                rel_path = str(item.get("path") or "").strip().replace("\\", "/")
                if not rel_path:
                    continue
                content = str(item.get("content") or "")
                path = _safe_join_workspace_worker(workspace_root, rel_path)
                if path not in backups:
                    if path.exists():
                        backups[path] = (True, path.read_text(encoding="utf-8", errors="ignore"))
                    else:
                        backups[path] = (False, "")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                touched.append(path)
                generated_paths.append(rel_path)
                await _emit("file_created", {"path": rel_path, "content": content})

            review_summary = str(plan_result.get("review") or "")
            if review_summary:
                await _emit("assistant_message", review_summary)

            if memory is not None:
                quality_status = str((plan_result.get("quality_gate") or {}).get("final_status") or "")
                try:
                    prd_total = float((plan_result.get("prd_score") or {}).get("total") or 0.0)
                except Exception:
                    prd_total = 0.0
                try:
                    visual_total = float((plan_result.get("visual_score") or {}).get("total") or 0.0)
                except Exception:
                    visual_total = 0.0
                memory.add(
                    query=str(data.get("task") or ""),
                    resolution=(
                        f"generated_files={len(generated_paths)}\n"
                        f"files={generated_paths[:80]}\n"
                        f"review={review_summary[:2000]}\n"
                        f"quality={quality_status}\n"
                        f"prd_total={prd_total}\n"
                        f"visual_total={visual_total}"
                    ),
                    metadata={"run_id": run_id, "mode": "worker_multi_agent"},
                )

            effective_framework = str(plan_result.get("framework") or "").strip().lower()
            if not effective_framework:
                names = {Path(p).name.lower() for p in generated_paths}
                if "pubspec.yaml" in names:
                    effective_framework = "flutter"
                elif "package.json" in names:
                    effective_framework = "react"
                elif "main.py" in names:
                    effective_framework = "python"
                elif "index.html" in names:
                    effective_framework = "html"
                else:
                    effective_framework = "html"
            smoke_gate = {"ok": True, "summary": "disabled", "framework": effective_framework, "checks": [], "blocking_issues": []}
            smoke_attempt = 0
            while smoke_check_enabled:
                await _emit("run_stage", {"stage": "smoke_check", "message": f"Running {effective_framework} smoke checks..."})
                smoke_gate = await asyncio.to_thread(
                    run_framework_smoke_check,
                    workspace=workspace_root,
                    framework=effective_framework,
                )
                await _emit(
                    "console_log",
                    {
                        "text": f"[smoke_gate] {smoke_gate.get('summary')}",
                        "level": "success" if smoke_gate.get("ok") else "error",
                    },
                )
                if smoke_gate.get("ok") is True:
                    break
                blocking = smoke_gate.get("blocking_issues")
                blocking_list = [str(x) for x in (list(blocking) if isinstance(blocking, list) else []) if str(x).strip()]
                failure_memory.add_case(
                    query=task_for_generation,
                    framework=effective_framework,
                    issues=blocking_list,
                    success=False,
                    resolution=f"smoke_summary={smoke_gate.get('summary')}",
                    metadata={"run_id": run_id, "stage": "smoke_gate", "attempt": smoke_attempt},
                )
                if smoke_attempt >= smoke_rework_budget:
                    raise RuntimeError(f"Smoke gate failed: {smoke_gate.get('summary')}")
                smoke_attempt += 1
                env_blockers = detect_environment_blockers(blocking_list)
                if env_blockers:
                    env_text = "; ".join(env_blockers[:6])
                    failure_memory.add_case(
                        query=task_for_generation,
                        framework=effective_framework,
                        issues=[str(x) for x in env_blockers],
                        success=False,
                        resolution="environment blocker detected",
                        metadata={"run_id": run_id, "stage": "smoke_gate", "attempt": smoke_attempt},
                    )
                    raise RuntimeError(
                        "Smoke gate failed due to missing runtime environment dependencies: "
                        f"{env_text}. Install required runtimes in backend environment first."
                    )
                await _emit(
                    "console_log",
                    {
                        "text": f"[smoke_gate] auto rework {smoke_attempt}/{smoke_rework_budget}",
                        "level": "warning",
                    },
                )
                rework_task = build_smoke_rework_task(
                    base_task=task_for_generation,
                    framework=effective_framework,
                    blocking_issues=blocking_list,
                    attempt=smoke_attempt,
                    budget=smoke_rework_budget,
                    is_game=_is_game_task(task_for_generation),
                )
                plan_result = await scheduler.run(
                    task=rework_task,
                    repo_map=repo_map_text,
                    ast_context=ast_context_text,
                    memory_hints=memory_hits,
                    framework=scheduler_framework,
                )
                # Re-apply rewritten artifacts before next smoke check.
                artifacts = plan_result.get("artifacts") if isinstance(plan_result, dict) else None
                if not isinstance(artifacts, list):
                    artifacts = []
                generated_paths = []
                for item in artifacts:
                    if not isinstance(item, dict):
                        continue
                    rel_path = str(item.get("path") or "").strip().replace("\\", "/")
                    if not rel_path:
                        continue
                    content = str(item.get("content") or "")
                    path = _safe_join_workspace_worker(workspace_root, rel_path)
                    if path not in backups:
                        if path.exists():
                            backups[path] = (True, path.read_text(encoding="utf-8", errors="ignore"))
                        else:
                            backups[path] = (False, "")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                    touched.append(path)
                    generated_paths.append(rel_path)
                    await _emit("file_created", {"path": rel_path, "content": content})
                effective_framework = str(plan_result.get("framework") or effective_framework).strip().lower() or effective_framework
            plan_result["smoke_gate"] = smoke_gate
            failure_memory.add_case(
                query=task_for_generation,
                framework=effective_framework,
                issues=[str(x) for x in (smoke_gate.get("blocking_issues") or []) if str(x).strip()],
                success=True,
                resolution=(
                    f"smoke_summary={smoke_gate.get('summary')}\n"
                    f"review={review_summary[:900]}\n"
                    f"quality={str((plan_result.get('quality_gate') or {}).get('final_status') or '')}"
                ),
                metadata={"run_id": run_id, "stage": "done", "attempts": smoke_attempt},
            )
            break
        except Exception as exc:
            # rollback touched files
            for path in reversed(touched):
                try:
                    existed, old = backups.get(path, (False, ""))
                    if existed:
                        path.write_text(old, encoding="utf-8")
                    elif path.exists():
                        path.unlink()
                except Exception:
                    pass
            await _emit("run_progress", f"[rollback] attempt {attempt} rolled back due to error: {exc}")
            failure_memory.add_case(
                query=task_for_generation,
                framework=str(scheduler_framework or ""),
                issues=[str(exc)],
                success=False,
                resolution=f"attempt={attempt} rollback",
                metadata={"run_id": run_id, "stage": "rollback"},
            )
            if attempt > retry_budget:
                ExecutionStore.update(
                    run_id,
                    status=STATUS_FAILED,
                    stage="failed",
                    progress=str(exc),
                    result={"error": str(exc), "code": "E_MULTI_AGENT_FAILED"},
                    metrics={"attempts": attempt, "retry_budget": retry_budget},
                )
                await _emit("run_error", {"error": str(exc), "code": "E_MULTI_AGENT_FAILED"})
                raise
            await _emit("run_progress", f"[retry] restarting multi-agent attempt {attempt + 1}/{retry_budget + 1}")
            await asyncio.sleep(min(1.5 * attempt, 5.0))

    result = {
        "report": str(plan_result.get("review") or ""),
        "graph": "",
        "files": generated_paths,
        "framework": str(plan_result.get("framework") or ""),
        "budget": plan_result.get("budget"),
        "quality_gate": plan_result.get("quality_gate"),
        "prd_score": plan_result.get("prd_score"),
        "visual_score": plan_result.get("visual_score"),
        "smoke_gate": plan_result.get("smoke_gate"),
    }
    from app.core.cache import cache

    cache.set(cache_key, result, ttl_s=data.get("cache_ttl_s"))
    ExecutionStore.update(
        run_id,
        status=STATUS_FINISHED,
        stage="done",
        progress="Completed.",
        result=result,
        metrics={
            "execution_mode": "worker_multi_agent",
            "generated_files": len(generated_paths),
            "retry_budget": retry_budget,
            "attempts": attempt,
            "repo_map": 1 if use_repo_map else 0,
            "ast_context": 1 if use_ast_context else 0,
            "experience_memory": 1 if use_memory else 0,
            "quality_gate_status": str((plan_result.get("quality_gate") or {}).get("final_status") or ""),
            "quality_gate_reworks": int((plan_result.get("quality_gate") or {}).get("auto_reworks") or 0),
            "prd_score_total": float((plan_result.get("prd_score") or {}).get("total") or 0.0),
            "visual_score_total": float((plan_result.get("visual_score") or {}).get("total") or 0.0),
            "smoke_gate_ok": 1 if (plan_result.get("smoke_gate") or {}).get("ok") else 0,
            "smoke_check_enabled": 1 if smoke_check_enabled else 0,
            "smoke_rework_budget": smoke_rework_budget,
        },
    )


def _extract_usage_metrics(messages) -> dict[str, int]:
    metrics = {"model_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for msg in messages or []:
        if getattr(msg, "role", None) != "assistant":
            continue
        metrics["model_calls"] += 1
        usage = getattr(msg, "metadata", {}).get("usage")
        if not isinstance(usage, dict):
            continue
        metrics["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
        metrics["completion_tokens"] += int(usage.get("completion_tokens") or 0)
        metrics["total_tokens"] += int(usage.get("total_tokens") or 0)
    return metrics


def _resolve_split_max_concurrency(
    requested: int | None, task_count: int, *, default_limit: int = 3
) -> int:
    if task_count <= 1:
        return 1
    env_value = os.getenv("REBOT_SPLIT_MAX_CONCURRENCY")
    if requested is not None:
        return max(1, min(int(requested), task_count))
    if env_value:
        try:
            return max(1, min(int(env_value), task_count))
        except Exception:
            pass
    return min(max(1, default_limit), task_count)


def _resolve_model_max_concurrency(
    *,
    requested: int | None,
    model: str,
    base_url: str | None,
) -> int:
    env_value = os.getenv("REBOT_MODEL_MAX_CONCURRENCY")
    if requested is not None:
        return max(1, int(requested))
    if env_value:
        try:
            return max(1, int(env_value))
        except Exception:
            pass
    model_l = (model or "").lower()
    base_l = (base_url or "").lower()
    is_slow = (
        "deepseek" in base_l
        or model_l.startswith("deepseek-")
        or "moonshot" in base_l
        or model_l.startswith("moonshot-")
        or "kimi" in model_l
    )
    if is_slow:
        return 2
    return 4


async def _run_chunks_limited(tasks: list[str], run_chunk, max_concurrency: int) -> list[str]:
    semaphore = asyncio.Semaphore(max(1, max_concurrency))
    results: list[str] = [""] * len(tasks)

    async def _run_one(idx: int, task: str) -> None:
        async with semaphore:
            results[idx] = await run_chunk(idx, task)

    await asyncio.gather(*(_run_one(i, t) for i, t in enumerate(tasks)))
    return results


async def _run_workflow_execution(run_id: str, data: dict[str, object]) -> None:
    ExecutionStore.update(run_id, status=STATUS_RUNNING, stage="workflow", progress="Executing workflow...")
    model_max_concurrency = _resolve_model_max_concurrency(
        requested=(
            int(data["model_max_concurrency"])
            if data.get("model_max_concurrency") is not None
            else None
        ),
        model=str(data["model"]),
        base_url=str(data["base_url"]),
    )
    model = create_chat_model(
        ModelConfig(
            api_key=str(data["api_key"]),
            model=str(data["model"]),
            base_url=str(data["base_url"]),
            max_concurrency=model_max_concurrency,
        ),
        provider=(str(data["provider"]) if data.get("provider") is not None else None),
    )
    workspace_root = Path(str(data["workspace"]))
    tools = {}
    if data.get("enable_file_tools", True):
        tools.update(
            {
                "list_files": ListFilesTool(),
                "read_file": ReadFileTool(root=workspace_root),
                "write_file": WriteFileTool(root=workspace_root),
                "replace_in_file": ReplaceInFileTool(root=workspace_root),
                "apply_patch": ApplyPatchTool(root=workspace_root),
            }
        )
    if data.get("enable_command_tools"):
        tools["run_tests"] = RunTestsTool(root=workspace_root)
    bus = get_event_bus()

    def emit(event: dict[str, object]) -> None:
        asyncio.create_task(bus.publish_event(run_id, event))

    registry = create_default_registry()
    trace = TraceCollector(run_id=run_id, sink=emit)
    ctx = ExecutionContext(model=model, tools=tools, events=emit, trace=trace)
    executor = WorkflowExecutor(registry=registry, ctx=ctx)
    workflow = WorkflowSpec.model_validate(data["workflow"])
    inputs = data.get("inputs") or {}
    result = await executor.run(workflow, inputs)
    payload = {"outputs": result.outputs, "node_outputs": result.node_outputs}
    from app.core.cache import cache

    cache_key = str(
        data.get("cache_key")
        or f"workflow:{data.get('provider')}:{data['model']}:{data['base_url']}:{data['workspace']}"
    )
    cache.set(cache_key, payload, ttl_s=data.get("cache_ttl_s"))
    ExecutionStore.update(run_id, status=STATUS_FINISHED, stage="done", progress="Completed.", result=payload)


async def _run_generate(run_id: str, data: dict[str, object]) -> None:
    ExecutionStore.update(run_id, status=STATUS_RUNNING, stage="init", progress="Starting generation...")
    from rebot.auto.generate import OneShotGenerator, GeneratorConfig
    bus = get_event_bus()
    await bus.publish_event(run_id, {"type": "run_start", "payload": {"job_type": "generate"}})
    thinking_chain = [
        "Analyze requirement and detect platform/language constraints.",
        "Build perspective context and retrieve vector memory.",
        "Generate compact file plan.",
        "Generate files incrementally in chunks.",
        "Write files and run quality/security checks.",
    ]
    await bus.publish_event(run_id, {"type": "thinking", "payload": thinking_chain})
    await bus.publish_event(
        run_id,
        {
            "type": "assistant_message",
            "payload": "Generating project in incremental mode (plan -> chunks -> continue).",
        },
    )
    stop_heartbeat = False

    async def _heartbeat() -> None:
        while not stop_heartbeat:
            await asyncio.sleep(8)
            if stop_heartbeat:
                break
            await bus.publish_event(
                run_id,
                {"type": "run_progress", "payload": "Generating files..."},
            )

    heartbeat_task = asyncio.create_task(_heartbeat())

    base_model_name = str(data["model"])
    base_url = str(data["base_url"])
    loop = asyncio.get_running_loop()

    def _token_cb(chunk) -> None:
        ExecutionStore.update(run_id, status=STATUS_STREAMING, stage="streaming", progress="Streaming model output...")
        asyncio.run_coroutine_threadsafe(
            bus.publish_event(run_id, {"type": "token", "payload": chunk.content}),
            loop,
        )

    def _build_model(model_name: str):
        model_max_concurrency = _resolve_model_max_concurrency(
            requested=(
                int(data["model_max_concurrency"])
                if data.get("model_max_concurrency") is not None
                else None
            ),
            model=model_name,
            base_url=base_url,
        )
        return create_chat_model(
            ModelConfig(
                api_key=str(data["api_key"]),
                model=model_name,
                base_url=base_url,
                max_concurrency=model_max_concurrency,
            ),
            provider=(str(data["provider"]) if data.get("provider") is not None else None),
        )

    def _build_cfg(*, degraded: bool) -> GeneratorConfig:
        return GeneratorConfig(
            language=str(data["language"]),
            platforms=list(data["platforms"]),
            include_ci=bool(data.get("include_ci", True)),
            include_security=False if degraded else bool(data.get("include_security", True)),
            execute_workflow=bool(data.get("execute_workflow", False)),
            workflow_inputs=dict(data.get("workflow_inputs") or {}),
            enable_file_tools=bool(data.get("enable_file_tools", True)),
            enable_command_tools=bool(data.get("enable_command_tools", False)),
            ai_codegen=bool(data.get("ai_codegen", True)),
            validate_commands=list(data.get("validate_commands") or []),
            domain_targets=list(data.get("domain_targets") or []),
            attention_scale=float(data.get("attention_scale", 1.0)),
            metagpt_chain=False if degraded else bool(data.get("metagpt_chain", True)),
            metagpt_native=False if degraded else bool(data.get("metagpt_native", False)),
            metagpt_native_repo=(
                str(data["metagpt_native_repo"])
                if data.get("metagpt_native_repo") is not None
                else None
            ),
            metagpt_native_rounds=int(data.get("metagpt_native_rounds", 5)),
            metagpt_native_investment=float(data.get("metagpt_native_investment", 3.0)),
            metagpt_native_only=False if degraded else bool(data.get("metagpt_native_only", False)),
            perspective=False if degraded else bool(data.get("perspective", True)),
            max_codegen_workers=(
                int(data["max_codegen_workers"])
                if data.get("max_codegen_workers") is not None
                else None
            ),
            max_files=(
                int(data["max_files"])
                if data.get("max_files") is not None
                else None
            ),
            max_file_chunks=(
                int(data["max_file_chunks"])
                if data.get("max_file_chunks") is not None
                else None
            ),
            max_refine_rounds=(
                int(data["max_refine_rounds"])
                if data.get("max_refine_rounds") is not None
                else None
            ),
        )
    def _progress(stage: str, message: str) -> None:
        ExecutionStore.update(run_id, stage=stage, progress=message)
        asyncio.run_coroutine_threadsafe(
            bus.publish_event(run_id, {"type": "run_stage", "payload": {"stage": stage, "message": message}}),
            loop,
        )
        asyncio.run_coroutine_threadsafe(
            bus.publish_event(run_id, {"type": "run_progress", "payload": f"[{stage}] {message}"}),
            loop,
        )

    try:
        attempt_specs: list[tuple[str, bool, str]] = []
        attempt_specs.append((base_model_name, False, "normal"))
        if base_model_name == "deepseek-reasoner":
            attempt_specs.append(("deepseek-chat", True, "fallback_model"))
        else:
            attempt_specs.append((base_model_name, True, "fallback_mode"))

        last_exc: Exception | None = None
        for idx, (model_name, degraded, label) in enumerate(attempt_specs, start=1):
            await bus.publish_event(
                run_id,
                {
                    "type": "run_stage",
                    "payload": {
                        "stage": "generate_attempt",
                        "message": f"Attempt {idx}/{len(attempt_specs)} mode={label} model={model_name}",
                    },
                },
            )
            try:
                model = _build_model(model_name)
                model.stream_callback = _token_cb
                generator = OneShotGenerator(model=model, root=Path(str(data["workspace"])))
                cfg = _build_cfg(degraded=degraded)
                await asyncio.to_thread(generator.generate, str(data["requirement"]), cfg, _progress)
                last_exc = None
                model.stream_callback = None
                break
            except Exception as exc:
                last_exc = exc
                await bus.publish_event(
                    run_id,
                    {
                        "type": "run_progress",
                        "payload": f"Attempt {idx} failed, retrying... ({exc})",
                    },
                )
                try:
                    model.stream_callback = None
                except Exception:
                    pass
                continue
        if last_exc is not None:
            raise last_exc
    finally:
        stop_heartbeat = True
        heartbeat_task.cancel()
    ExecutionStore.update(run_id, status=STATUS_FINALIZING, stage="finalizing", progress="Finalizing generated project...")
    payload = {"workspace": str(data["workspace"]), "status": "generated"}
    from app.core.cache import cache

    cache_key = str(
        data.get("cache_key")
        or (
            f"generate:{data.get('provider')}:{data['model']}:{data['base_url']}:"
            f"{data['workspace']}:{data['requirement']}"
        )
    )
    cache.set(cache_key, payload, ttl_s=data.get("cache_ttl_s"))
    ExecutionStore.update(run_id, status=STATUS_FINISHED, stage="done", progress="Completed.", result=payload)
    await bus.publish_event(
        run_id,
        {"type": "assistant_message", "payload": "Project generated successfully. Starting preview..."},
    )
    await bus.publish_event(run_id, {"type": "run_end", "payload": payload})


if __name__ == "__main__":
    asyncio.run(run_worker())
