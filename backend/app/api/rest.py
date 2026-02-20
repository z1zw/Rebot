from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Optional, Awaitable, Callable
from pathlib import Path
import asyncio
import os
import json
import re
import subprocess
import shutil
import time
import tempfile
import zipfile
import hashlib
import hmac
import urllib.request
import urllib.error
from urllib.parse import urlparse

from rebot import ModelConfig, CodingAgent
from rebot.core.messages import Message
from rebot.models.providers import create_chat_model
from rebot.core.trace import TraceCollector
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
from app.core.tasks import TaskQueue, get_task_queue
from app.core.cache import cache
from app.core.schemas import ChunkResult
from app.core.devserver import DevServerManager
from app.core.startup_manager import StartupManager
from app.core.emulator import EmulatorManager
from app.core.process_sandbox import run_checked, split_command
from app.core.logging import get_logger
from app.core.metrics import observe_operation
from app.core.llm_routing import normalize_llm_selection
from app.core.smoke_gate import run_framework_smoke_check
from app.core.smoke_rework import build_smoke_rework_task, detect_environment_blockers
from app.intel.repo_map import RepoMapBuilder
from app.intel.ast_index import ASTCodeIndexer
from app.intel.experience_memory import ExperienceMemory
from app.intel.failure_memory import FailureMemory
from app.orchestration.multi_agent_scheduler import MultiAgentScheduler
from app.integrations.autogpt_catalog import list_agents as autogpt_list_agents, import_agent_to_workspace
from app.integrations.autogpt_workflow_adapter import analyze_agent_workflow, execute_workflow_trace
from app.api.models import (
    DevServerLogsRequest,
    DevServerRestartRequest,
    DevServerResponse,
    DevServerStartRequest,
    DevServerStatusRequest,
    DevServerStopRequest,
    EmulatorStartRequest,
    EmulatorStopRequest,
    ExecuteResponse,
    FileDeleteRequest,
    FileListRequest,
    FileReadRequest,
    FileRepairRequest,
    FileWriteRequest,
    SecurityTestRequest,
)
from app.api.services.preview_service import await_preview_health as _await_preview_health
from app.api.services.security_service import run_security_test as _run_security_test
from app.api.services.workspace_service import (
    detect_entrypoint as _detect_entrypoint,
    ensure_entrypoint_alignment as _ensure_entrypoint_alignment,
    normalize_and_validate_path as _normalize_and_validate_path,
    repair_workspace_layout as _repair_workspace_layout,
    safe_join_workspace as _safe_join_workspace,
)

router = APIRouter()
logger = get_logger(__name__)

Emit = Callable[[str, Any], Awaitable[None]]

TERMINAL_STATUSES = {STATUS_FINISHED, STATUS_FAILED, STATUS_CANCELLED}


class ExecuteRequest(BaseModel):
    task: str
    project_id: str | None = None
    autogpt_agent_id: str | None = None
    autogpt_workflow_enabled: bool = False
    api_key: str
    provider: str | None = None
    model: str = "gpt-4o-mini"
    model_max_concurrency: int | None = None
    base_url: str = "https://api.openai.com/v1"
    workspace: str
    dialog_mode: str | None = None
    attention: float | None = None
    review_mode: bool = False
    cache_key: str | None = None
    stream: bool = True
    max_context_chars: int | None = 32000
    max_context_tokens: int | None = None
    context_compress_type: str | None = "graph_sparse"
    context_head_ratio: float | None = 0.25
    context_matrix_rows: int | None = None
    context_matrix_cols: int | None = None
    context_sketch_dim: int | None = None
    tool_max_workers: int | None = None
    split_task: bool = False
    split_chunk_chars: int = 800
    split_max_concurrency: int | None = None
    metagpt_native: bool = False
    metagpt_native_repo: str | None = None
    metagpt_native_rounds: int = 5
    metagpt_native_investment: float = 3.0
    metagpt_native_only: bool = False
    cache_ttl_s: int | None = None


class ProjectRunRequest(BaseModel):
    task: str
    project_id: str | None = None
    project_type: str | None = None  # user-selected project type
    framework: str | None = None  # user-selected framework (flutter, react, vue, etc.)
    autogpt_agent_id: str | None = None
    autogpt_workflow_enabled: bool = False
    api_key: str
    provider: str | None = None
    model: str = "gpt-4o-mini"
    model_max_concurrency: int | None = None
    base_url: str = "https://api.openai.com/v1"
    workspace: str | None = None
    dialog_mode: str | None = None
    attention: float | None = None
    review_mode: bool = False
    cache_key: str | None = None
    stream: bool = True
    max_context_chars: int | None = 32000
    max_context_tokens: int | None = None
    context_compress_type: str | None = "graph_sparse"
    context_head_ratio: float | None = 0.25
    context_matrix_rows: int | None = None
    context_matrix_cols: int | None = None
    context_sketch_dim: int | None = None
    tool_max_workers: int | None = None
    split_task: bool = False
    split_chunk_chars: int = 800
    split_max_concurrency: int | None = None
    metagpt_native: bool = False
    metagpt_native_repo: str | None = None
    metagpt_native_rounds: int = 5
    metagpt_native_investment: float = 3.0
    metagpt_native_only: bool = False
    cache_ttl_s: int | None = None
    multi_agent: bool = True
    repo_map: bool = True
    experience_memory: bool = True
    multi_agent_workers: int | None = None
    role_model_overrides: dict[str, dict[str, Any]] | None = None
    max_token_budget: int | None = None
    max_cost_budget: float | None = None
    checkpoint_enabled: bool = True
    smoke_check_enabled: bool = True
    smoke_rework_budget: int = 2
    priority: int | None = None


class WorkflowExecuteRequest(BaseModel):
    workflow: WorkflowSpec
    inputs: dict[str, Any] = {}
    api_key: str
    provider: str | None = None
    model: str = "gpt-4o-mini"
    model_max_concurrency: int | None = None
    base_url: str = "https://api.openai.com/v1"
    workspace: str
    enable_file_tools: bool = True
    enable_command_tools: bool = False
    cache_key: str | None = None
    cache_ttl_s: int | None = None


class GenerateRequest(BaseModel):
    requirement: str
    language: str
    platforms: list[str]
    api_key: str
    provider: str | None = None
    model: str = "gpt-4o-mini"
    model_max_concurrency: int | None = None
    base_url: str = "https://api.openai.com/v1"
    workspace: str
    include_ci: bool = True
    include_security: bool = True
    execute_workflow: bool = False
    workflow_inputs: dict[str, Any] = {}
    enable_file_tools: bool = True
    enable_command_tools: bool = False
    ai_codegen: bool = True
    validate_commands: list[str] = []
    domain_targets: list[str] = []
    attention_scale: float = 1.0
    metagpt_chain: bool = False
    metagpt_native: bool = False
    metagpt_native_repo: str | None = None
    metagpt_native_rounds: int = 5
    metagpt_native_investment: float = 3.0
    metagpt_native_only: bool = False
    perspective: bool = True
    max_codegen_workers: int | None = None
    max_files: int | None = None
    max_file_chunks: int | None = None
    max_refine_rounds: int | None = None
    cache_key: str | None = None
    cache_ttl_s: int | None = None


class RunRequest(BaseModel):
    task: str
    project_id: str | None = None
    project_type: str | None = None
    framework: str | None = None  # user-selected framework (flutter, react, vue, etc.)
    autogpt_agent_id: str | None = None
    autogpt_workflow_enabled: bool = False
    api_key: str
    provider: str | None = None
    model: str = "gpt-4o-mini"
    model_max_concurrency: int | None = None
    base_url: str = "https://api.openai.com/v1"
    workspace: str
    cache_key: str | None = None
    cache_ttl_s: int | None = None
    multi_agent: bool = True
    repo_map: bool = True
    experience_memory: bool = True
    multi_agent_workers: int | None = None
    role_model_overrides: dict[str, dict[str, Any]] | None = None
    max_token_budget: int | None = None
    max_cost_budget: float | None = None
    checkpoint_enabled: bool = True
    smoke_check_enabled: bool = True
    smoke_rework_budget: int = 2
    priority: int | None = None
    resume_from_run_id: str | None = None
    resume_checkpoint_stage: str | None = None


class ProjectCloneRequest(BaseModel):
    repo_url: str
    destination: str | None = None
    branch: str | None = None
    depth: int = 1


class TemplateMarketSaveRequest(BaseModel):
    workspace: str
    name: str
    description: str | None = None
    tags: list[str] | None = None
    framework: str | None = None
    project_type: str | None = None


class TemplateMarketImportRequest(BaseModel):
    source_path: str
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    framework: str | None = None
    project_type: str | None = None


class TemplateMarketOpenRequest(BaseModel):
    template_id: str
    destination: str | None = None
    name: str | None = None
    framework: str | None = None
    project_type: str | None = None


class PluginInstallRequest(BaseModel):
    source_path: str


class PluginUpgradeRequest(BaseModel):
    plugin_id: str
    source_path: str


class PluginRollbackRequest(BaseModel):
    plugin_id: str


class PluginToggleRequest(BaseModel):
    plugin_id: str
    enabled: bool = True


class PluginExecutionRequest(BaseModel):
    plugin_id: str
    operation: str
    args: dict[str, Any] = {}
    workspace: str | None = None


class PluginSdkInitRequest(BaseModel):
    destination: str
    plugin_id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    permissions: list[str] = []


class AutoGPTImportRequest(BaseModel):
    agent_id: str
    workspace: str


class AutoGPTWorkflowAnalyzeRequest(BaseModel):
    agent_id: str


class LlmProbeRequest(BaseModel):
    api_key: str
    provider: str | None = None
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    prompt: str = "Reply with OK"
    timeout_s: float = 30.0


def _normalize_execute_request(req: ExecuteRequest) -> ExecuteRequest:
    updates: dict[str, Any] = {}
    task_len = len((req.task or "").strip())
    if not req.split_task and task_len > 900:
        updates["split_task"] = True
        if req.split_chunk_chars < 900:
            updates["split_chunk_chars"] = 900
    if req.max_context_chars is None and req.max_context_tokens is not None:
        try:
            updates["max_context_chars"] = max(4096, int(req.max_context_tokens) * 4)
        except Exception:
            pass
    if (
        req.context_matrix_rows is None
        or req.context_matrix_cols is None
        or req.context_sketch_dim is None
    ):
        rows, cols, sketch = _adaptive_matrix_profile(task_len)
        if req.context_matrix_rows is None:
            updates["context_matrix_rows"] = rows
        if req.context_matrix_cols is None:
            updates["context_matrix_cols"] = cols
        if req.context_sketch_dim is None:
            updates["context_sketch_dim"] = sketch
    if not updates:
        return req
    return req.model_copy(update=updates)


def _adaptive_matrix_profile(task_len: int) -> tuple[int, int, int]:
    # Small input: prefer speed. Large input: preserve more structure.
    if task_len <= 800:
        return 6, 6, 32
    if task_len <= 2400:
        return 8, 8, 64
    return 12, 12, 128


@router.post("/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest):
    run_req = RunRequest(
        task=req.task,
        project_id=req.project_id,
        autogpt_agent_id=req.autogpt_agent_id,
        autogpt_workflow_enabled=req.autogpt_workflow_enabled,
        api_key=req.api_key,
        provider=req.provider,
        model=req.model,
        model_max_concurrency=req.model_max_concurrency,
        base_url=req.base_url,
        workspace=req.workspace,
        cache_key=req.cache_key,
        cache_ttl_s=req.cache_ttl_s,
        multi_agent=True,
        repo_map=True,
        experience_memory=True,
    )
    return await run_autonomous(run_req)





def _project_run_request_to_execute(project_id: str, req: ProjectRunRequest) -> ExecuteRequest:
    return ExecuteRequest(
        task=req.task,
        project_id=req.project_id or project_id,
        autogpt_agent_id=req.autogpt_agent_id,
        autogpt_workflow_enabled=req.autogpt_workflow_enabled,
        api_key=req.api_key,
        provider=req.provider,
        model=req.model,
        model_max_concurrency=req.model_max_concurrency,
        base_url=req.base_url,
        workspace=req.workspace or f"./{project_id}",
        dialog_mode=req.dialog_mode,
        attention=req.attention,
        review_mode=req.review_mode,
        cache_key=req.cache_key,
        stream=req.stream,
        max_context_chars=req.max_context_chars,
        max_context_tokens=req.max_context_tokens,
        context_compress_type=req.context_compress_type,
        context_head_ratio=req.context_head_ratio,
        context_matrix_rows=req.context_matrix_rows,
        context_matrix_cols=req.context_matrix_cols,
        context_sketch_dim=req.context_sketch_dim,
        tool_max_workers=req.tool_max_workers,
        split_task=req.split_task,
        split_chunk_chars=req.split_chunk_chars,
        split_max_concurrency=req.split_max_concurrency,
        metagpt_native=req.metagpt_native,
        metagpt_native_repo=req.metagpt_native_repo,
        metagpt_native_rounds=req.metagpt_native_rounds,
        metagpt_native_investment=req.metagpt_native_investment,
        metagpt_native_only=req.metagpt_native_only,
        cache_ttl_s=req.cache_ttl_s,
    )


async def _run_event_stream(request: Request, run_id: str):
    bus = get_event_bus()
    run_queue = await bus.subscribe(run_id)
    current_stage: str | None = None
    done_emitted = False

    try:
        rec = ExecutionStore.get(run_id)
        initial_stage = rec.stage if rec and rec.stage else "queued"
        initial_status = rec.status if rec and rec.status else "running"

        yield _sse_frame("stage_update", {"stage": initial_stage, "status": "running" if initial_status == STATUS_QUEUED else initial_status, "run_id": run_id})
        yield _sse_frame(
            "agent_message",
            {
                "agent": "Alex",
                "role": "Engineer",
                "content": f"Task accepted. run_id={run_id}",
                "step": 1,
                "total_steps": 5,
            },
        )

        while True:
            if await request.is_disconnected():
                break
            batch = await bus.next_for_run(run_queue, timeout=1.0)
            if batch is None:
                rec = ExecutionStore.get(run_id)
                if rec and rec.status in TERMINAL_STATUSES:
                    if not done_emitted:
                        done_status = "completed" if rec.status == STATUS_FINISHED else rec.status
                        done_payload = {"status": done_status, "run_id": run_id}
                        rec_result = rec.result if isinstance(rec.result, dict) else {}
                        if isinstance(rec_result, dict):
                            done_payload["preview_url"] = str(rec_result.get("preview_url") or "")
                            done_payload["workspace"] = str(rec_result.get("workspace") or "")
                            if isinstance(rec_result.get("quality_gate"), dict):
                                done_payload["quality_gate"] = rec_result.get("quality_gate")
                            if isinstance(rec_result.get("prd_score"), dict):
                                done_payload["prd_score"] = rec_result.get("prd_score")
                            if isinstance(rec_result.get("visual_score"), dict):
                                done_payload["visual_score"] = rec_result.get("visual_score")
                            if isinstance(rec_result.get("smoke_gate"), dict):
                                done_payload["smoke_gate"] = rec_result.get("smoke_gate")
                        yield _sse_frame("done", done_payload)
                    break
                yield ": ping\n\n"
                continue

            events = batch.get("events") or []
            for ev in events:
                mapped, current_stage = _map_bus_event_to_sse(ev, current_stage)
                for e_name, payload in mapped:
                    payload = dict(payload)
                    payload.setdefault("run_id", run_id)
                    yield _sse_frame(e_name, payload)
                    if e_name == "done":
                        done_emitted = True
            if done_emitted:
                break
    finally:
        bus.unsubscribe(run_id, run_queue)


@router.post("/projects/{project_id}/run", response_model=ExecuteResponse)
async def run_project(project_id: str, req: ProjectRunRequest):
    run_req = RunRequest(
        task=req.task,
        project_id=req.project_id or project_id,
        project_type=req.project_type,
        framework=req.framework,
        autogpt_agent_id=req.autogpt_agent_id,
        autogpt_workflow_enabled=req.autogpt_workflow_enabled,
        api_key=req.api_key,
        provider=req.provider,
        model=req.model,
        model_max_concurrency=req.model_max_concurrency,
        base_url=req.base_url,
        workspace=req.workspace or f"./{project_id}",
        cache_key=req.cache_key,
        cache_ttl_s=req.cache_ttl_s,
        multi_agent=req.multi_agent,
        repo_map=req.repo_map,
        experience_memory=req.experience_memory,
        multi_agent_workers=req.multi_agent_workers,
        role_model_overrides=req.role_model_overrides,
        max_token_budget=req.max_token_budget,
        max_cost_budget=req.max_cost_budget,
        checkpoint_enabled=req.checkpoint_enabled,
        smoke_check_enabled=req.smoke_check_enabled,
        smoke_rework_budget=req.smoke_rework_budget,
        priority=req.priority,
    )
    return await run_autonomous(run_req)


@router.get("/run/{id}/stream")
async def stream_run(
    id: str,
    request: Request,
    task: str | None = None,
    api_key: str | None = None,
    provider: str | None = None,
    model: str = "gpt-4o-mini",
    base_url: str = "https://api.openai.com/v1",
    workspace: str | None = None,
    dialog_mode: str | None = None,
    attention: float | None = None,
    review_mode: bool = False,
    split_task: bool = False,
    split_chunk_chars: int = 800,
    split_max_concurrency: int | None = None,
    model_max_concurrency: int | None = None,
    max_context_chars: int | None = 32000,
    max_context_tokens: int | None = None,
    context_compress_type: str | None = "graph_sparse",
    context_head_ratio: float | None = 0.25,
    context_matrix_rows: int | None = None,
    context_matrix_cols: int | None = None,
    context_sketch_dim: int | None = None,
):
    run_id = id
    if task is not None:
        if not api_key:
            return StreamingResponse(
                iter([_sse_frame("done", {"status": "failed", "error": "api_key is required when task is provided"})]),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        req = ProjectRunRequest(
            task=task,
            api_key=api_key,
            provider=provider,
            model=model,
            model_max_concurrency=model_max_concurrency,
            base_url=base_url,
            workspace=workspace,
            dialog_mode=dialog_mode,
            attention=attention,
            review_mode=review_mode,
            split_task=split_task,
            split_chunk_chars=split_chunk_chars,
            split_max_concurrency=split_max_concurrency,
            max_context_chars=max_context_chars,
            max_context_tokens=max_context_tokens,
            context_compress_type=context_compress_type,
            context_head_ratio=context_head_ratio,
            context_matrix_rows=context_matrix_rows,
            context_matrix_cols=context_matrix_cols,
            context_sketch_dim=context_sketch_dim,
            stream=True,
        )
        resp = await run_project(id, req)
        run_id = resp.run_id

    return StreamingResponse(
        _run_event_stream(request, run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/run", response_model=ExecuteResponse)
async def run_autonomous(req: RunRequest):
    started_at = time.perf_counter()
    normalized_provider, normalized_base_url = normalize_llm_selection(
        provider=req.provider,
        model=req.model,
        base_url=req.base_url,
    )
    if normalized_provider != req.provider or normalized_base_url != req.base_url:
        req = req.model_copy(update={"provider": normalized_provider, "base_url": normalized_base_url})
    request_key = (
        f"run:{req.project_id or '-'}:{req.project_type or '-'}:{req.provider}:{req.model}:{req.base_url}:{req.workspace}:{req.task}:"
        f"autogpt:{req.autogpt_agent_id or '-'}:wf:{1 if req.autogpt_workflow_enabled else 0}"
    )
    existing = ExecutionStore.find_active_by_request_key(request_key)
    if existing is not None:
        observe_operation("run_autonomous", "deduplicated", time.perf_counter() - started_at)
        logger.info(
            "run_request_deduplicated",
            extra={"event": "run_request_deduplicated", "run_id": existing.run_id, "project_id": req.project_id},
        )
        return ExecuteResponse(run_id=existing.run_id)
    record = ExecutionStore.create()
    priority = max(0, min(int(req.priority or 5), 10))
    request_payload = req.model_dump()
    request_payload["job_type"] = "agent"
    request_payload["priority"] = priority
    ExecutionStore.update(
        record.run_id,
        metrics={
            "request_key": request_key,
            "job_type": "autonomous",
            "priority": priority,
            "request_payload": request_payload,
        },
        status=STATUS_QUEUED,
        stage=STATUS_QUEUED,
        progress="Task queued.",
    )
    queue = get_task_queue()
    if queue is None:
        asyncio.create_task(_execute_autonomous_run(record.run_id, req))
    else:
        await queue.enqueue(record.run_id, request_payload)
    observe_operation("run_autonomous", "queued", time.perf_counter() - started_at)
    logger.info(
        "run_request_queued",
        extra={"event": "run_request_queued", "run_id": record.run_id, "project_id": req.project_id},
    )
    return ExecuteResponse(run_id=record.run_id)


def _sse_frame(event: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"


def _emit_stage_transition(next_stage: str, current_stage: str | None) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    if current_stage and current_stage != next_stage:
        out.append(("stage_update", {"stage": current_stage, "status": "done"}))
    out.append(("stage_update", {"stage": next_stage, "status": "running"}))
    return out


def _map_bus_event_to_sse(
    ev: dict[str, Any],
    current_stage: str | None,
) -> tuple[list[tuple[str, dict[str, Any]]], str | None]:
    out: list[tuple[str, dict[str, Any]]] = []
    et = str(ev.get("type") or "")
    payload = ev.get("payload")

    if et == "run_stage" and isinstance(payload, dict):
        stage = str(payload.get("stage") or "agent")
        out.extend(_emit_stage_transition(stage, current_stage))
        msg = str(payload.get("message") or f"Entering stage: {stage}")
        out.append(("agent_message", {"agent": "Alex", "role": "Engineer", "content": msg, "step": 1, "total_steps": 5}))
        return out, stage

    if et == "run_progress" and payload is not None:
        out.append(("agent_message", {"agent": "Alex", "role": "Engineer", "content": str(payload), "step": 1, "total_steps": 5}))
        return out, current_stage

    if et == "assistant_message":
        out.append(("agent_message", {"agent": "Alex", "role": "Engineer", "content": str(payload or ""), "step": 1, "total_steps": 5}))
        return out, current_stage

    if et == "chunk_start":
        step = int(payload) + 1 if isinstance(payload, int) else 1
        out.append(("agent_message", {"agent": "Alex", "role": "Engineer", "content": f"Starting chunk {step}...", "step": step, "total_steps": 5}))
        return out, current_stage

    if et == "chunk_end" and isinstance(payload, dict):
        step = int(payload.get("index") or 0) + 1
        report = str(payload.get("report") or "")
        if report:
            out.append(("agent_message", {"agent": "Alex", "role": "Engineer", "content": report, "step": step, "total_steps": 5}))
        changes = payload.get("changes")
        if isinstance(changes, list):
            for item in changes:
                if not isinstance(item, dict):
                    continue
                path = str(item.get("path") or "")
                if not path:
                    continue
                status = str(item.get("status") or "done")
                content = str(item.get("content") or "")
                if status in {"writing", "pending", "started"}:
                    out.append(("file_generating", {"path": path, "status": "writing"}))
                else:
                    out.append(("file_done", {"path": path, "status": "done", "content": content}))
        return out, current_stage

    if et == "run_error" and isinstance(payload, dict):
        msg = str(payload.get("error") or "Run failed")
        out.append(("console_log", {"text": msg, "level": "error"}))
        out.append(("done", {"status": "failed"}))
        return out, current_stage

    if et == "run_end":
        if isinstance(payload, dict):
            url = str(payload.get("url") or payload.get("preview_url") or "")
            if url:
                out.append(("preview_ready", {"url": url}))
        out.append(("done", {"status": "completed"}))
        return out, current_stage

    if et == "cache_hit":
        out.append(("agent_message", {"agent": "Alex", "role": "Engineer", "content": "Cache hit. Returning cached result.", "step": 1, "total_steps": 1}))
        out.append(("done", {"status": "completed"}))
        return out, current_stage

    if et == "token" and payload is not None:
        chunk = str(payload or "")
        if not _is_useful_thought_chunk(chunk):
            return out, current_stage
        chunk = chunk.strip()
        if len(chunk) > 2400:
            chunk = chunk[-2400:]
        out.append(("agent_thought", {"data": chunk}))
        return out, current_stage

    if et == "agent_thought":
        out.append(("agent_thought", {"data": str(payload or "")}))
        return out, current_stage

    if et == "file_created" and isinstance(payload, dict):
        out.append(("file_created", payload))
        return out, current_stage

    if et == "file_generating" and isinstance(payload, dict):
        out.append(("file_generating", payload))
        return out, current_stage

    if et == "file_done" and isinstance(payload, dict):
        out.append(("file_done", payload))
        return out, current_stage

    if et == "console_log":
        if isinstance(payload, dict):
            out.append(("console_log", payload))
        else:
            out.append(("console_log", {"text": str(payload), "level": "default"}))
        return out, current_stage

    if et in {
        "quality_gate_report",
        "quality_gate_cycle",
        "prd_score",
        "visual_score",
        "smoke_gate",
        "plan_summary",
        "plan_review",
        "plan_ast_deps",
        "preview_health",
        "checkpoint_saved",
    }:
        if isinstance(payload, dict):
            out.append((et, payload))
        else:
            out.append((et, {"value": payload}))
        return out, current_stage

    if et == "done":
        if isinstance(payload, dict):
            out.append(("done", payload))
        else:
            out.append(("done", {"status": "completed"}))
        return out, current_stage

    if et == "model_start" and isinstance(payload, dict):
        messages = payload.get("messages")
        if isinstance(messages, list):
            digest_text = _extract_context_digest(messages)
            if digest_text:
                out.append(("context_digest", {"xml": digest_text}))
        return out, current_stage

    return out, current_stage


def _extract_context_digest(messages: list[Any]) -> str:
    for msg in messages:
        if isinstance(msg, dict):
            role = str(msg.get("role") or "")
            content = str(msg.get("content") or "")
        else:
            role = str(getattr(msg, "role", "") or "")
            content = str(getattr(msg, "content", "") or "")
        if role != "system":
            continue
        if "<context_digest>" in content:
            return content[:6000]
    return ""


def _strip_code_fences(text: str) -> str:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return raw.strip()


def _is_useful_thought_chunk(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if len(t) <= 24 and "\n" not in t:
        return False
    lines = [x.strip() for x in t.replace("\r\n", "\n").split("\n") if x.strip()]
    if not lines:
        return False
    short = sum(1 for x in lines if len(x) <= 2)
    codeish = sum(
        1
        for x in lines
        if re.search(r"^(const|let|var|function|class|import|export|return|if\s*\(|for\s*\(|while\s*\()", x, re.IGNORECASE)
    )
    letters = len(re.findall(r"[A-Za-z\u4e00-\u9fff]", t))
    symbols = len(re.findall(r"[{};<>:=/_\\\[\]\(\)]", t))
    if short >= 10 and len(lines) >= 12:
        return False
    if codeish >= max(3, int(len(lines) * 0.35)):
        return False
    if symbols > max(18, int(max(letters, 1) * 0.6)):
        return False
    words = len(re.findall(r"[A-Za-z\u4e00-\u9fff0-9]+", t))
    if words <= 4 and "\n" not in t and re.search(r"[.!?。！？:：]$", t) is None:
        return False
    return True


async def _initialize_framework_project(workspace: Path, framework: str, emit) -> None:
    """Run framework-specific initialization commands after file generation."""
    import shutil
    
    async def _run_cmd(cmd: str, desc: str) -> bool:
        """Run a command and emit progress."""
        await emit("console_log", {"text": f"[init] {desc}...", "level": "info"})
        try:
            cmd_list = split_command(cmd)
            completed = await asyncio.to_thread(
                run_checked,
                cmd_list,
                cwd=workspace,
                timeout=120,
                capture_output=True,
                text=True,
            )
            if completed.returncode == 0:
                await emit("console_log", {"text": f"[init] {desc} completed", "level": "success"})
                return True
            else:
                err = (completed.stderr or "")[:500]
                await emit("console_log", {"text": f"[init] {desc} failed: {err}", "level": "warning"})
                return False
        except subprocess.TimeoutExpired:
            await emit("console_log", {"text": f"[init] {desc} timed out", "level": "warning"})
            return False
        except Exception as exc:
            await emit("console_log", {"text": f"[init] {desc} error: {exc}", "level": "warning"})
            return False

    if framework == "flutter":
        # Check if flutter is available
        flutter_cmd = "flutter.bat" if os.name == "nt" else "flutter"
        if shutil.which(flutter_cmd) or shutil.which("flutter"):
            pubspec = workspace / "pubspec.yaml"
            if pubspec.exists():
                # Enable web platform if not exists
                web_dir = workspace / "web"
                if not web_dir.exists():
                    await _run_cmd("flutter create --platforms web .", "Flutter enable web platform")
                await _run_cmd("flutter pub get", "Flutter pub get")
            else:
                await emit("console_log", {"text": "[init] Flutter: missing pubspec.yaml, skipping pub get", "level": "warning"})
        else:
            await emit("console_log", {"text": "[init] Flutter SDK not found, skipping initialization", "level": "warning"})
    
    elif framework in {"react", "vue", "nextjs", "uniapp"}:
        # Check if npm/node is available
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        if shutil.which(npm_cmd) or shutil.which("npm"):
            pkg = workspace / "package.json"
            if pkg.exists():
                node_modules = workspace / "node_modules"
                if not node_modules.exists():
                    await _run_cmd("npm install", "npm install")
            else:
                await emit("console_log", {"text": f"[init] {framework}: missing package.json, skipping npm install", "level": "warning"})
        else:
            await emit("console_log", {"text": "[init] npm not found, skipping initialization", "level": "warning"})
    
    elif framework == "python":
        # Check for requirements.txt
        reqs = workspace / "requirements.txt"
        if reqs.exists():
            pip_cmd = "pip" if shutil.which("pip") else "pip3"
            if shutil.which(pip_cmd):
                await _run_cmd(f"{pip_cmd} install -r requirements.txt", "pip install requirements")
            else:
                await emit("console_log", {"text": "[init] pip not found, skipping requirements install", "level": "warning"})


def _guess_framework_from_files(paths: list[str]) -> str:
    s = {Path(p).name.lower() for p in paths if p}
    full = {p.lower() for p in paths if p}
    if "pubspec.yaml" in s or any(p.endswith("/main.dart") for p in full):
        return "flutter"
    if "next.config.js" in s:
        return "nextjs"
    if "pages.json" in s or "manifest.json" in s:
        return "uniapp"
    if "package.json" in s:
        return "react"
    if "index.html" in s:
        return "html"
    return "html"


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


def _audit_and_fix_html_runtime(root: Path) -> dict[str, Any]:
    root = root.resolve()
    index = root / "index.html"
    if not index.exists():
        alt = root / "frontend" / "index.html"
        if alt.exists():
            index = alt
        else:
            return {"healthy": False, "issues": ["entry_point_missing:index.html"], "fixed": []}

    html = index.read_text(encoding="utf-8", errors="ignore")
    base_dir = index.parent
    fixed: list[str] = []
    issues: list[str] = []
    changed = False

    # Normalize leading slash static refs to relative refs under current root.
    for tag, attr in (("script", "src"), ("link", "href")):
        pat = re.compile(rf"(<{tag}\b[^>]*\b{attr}\s*=\s*[\"'])([^\"']+)([\"'][^>]*>)", re.IGNORECASE)
        def _normalize_ref(m: re.Match[str]) -> str:
            nonlocal changed
            head, ref, tail = m.group(1), m.group(2).strip(), m.group(3)
            if re.match(r"^(https?:)?//", ref) or ref.startswith("data:") or ref.startswith("#"):
                return m.group(0)
            nref = ref
            if ref.startswith("/"):
                candidate = base_dir / ref.lstrip("/")
                if candidate.exists():
                    nref = f"./{ref.lstrip('/')}"
                    if nref != ref:
                        fixed.append(f"{tag}:{ref}->{nref}")
                        changed = True
            return f"{head}{nref}{tail}"
        html = pat.sub(_normalize_ref, html)

    # Ensure deferred script execution for DOM-safe startup.
    html2 = re.sub(
        r"(?i)<script(?![^>]*\bdefer\b)([^>]*\bsrc\s*=\s*[\"'][^\"']+[\"'][^>]*)>",
        r"<script defer\1>",
        html,
    )
    if html2 != html:
        fixed.append("script:added_defer")
        html = html2
        changed = True

    # Auto-inject common assets when missing.
    if re.search(r"(?i)<script[^>]+src=", html) is None and (base_dir / "game.js").exists():
        html = re.sub(r"(?i)</body>", '<script defer src="./game.js"></script>\n</body>', html, count=1)
        fixed.append("script:inject_game.js")
        changed = True
    if re.search(r"(?i)<link[^>]+href=", html) is None and (base_dir / "styles.css").exists():
        html = re.sub(r"(?i)</head>", '<link rel="stylesheet" href="./styles.css">\n</head>', html, count=1)
        fixed.append("style:inject_styles.css")
        changed = True

    # Validate local refs after normalization/injection.
    ref_pat = re.compile(r"""(?i)\b(?:src|href)\s*=\s*["']([^"']+)["']""")
    refs = ref_pat.findall(html)
    for ref in refs:
        r = ref.strip()
        if not r or re.match(r"^(https?:)?//", r) or r.startswith("data:") or r.startswith("#"):
            continue
        p = (base_dir / r.lstrip("./")).resolve()
        if not p.exists():
            issues.append(f"missing_asset:{r}")

    if changed:
        index.write_text(html, encoding="utf-8")

    return {"healthy": len(issues) == 0, "issues": issues, "fixed": fixed, "entry": str(index)}


def _guess_id_alias(missing: str, ids: set[str]) -> str | None:
    if missing in ids:
        return missing
    if missing.endswith("-btn"):
        base = missing[:-4]
        if base in ids:
            return base
    if f"{missing}-btn" in ids:
        return f"{missing}-btn"
    miss_norm = re.sub(r"[^a-z0-9]", "", missing.lower())
    if not miss_norm:
        return None
    for cand in ids:
        cand_norm = re.sub(r"[^a-z0-9]", "", cand.lower())
        if cand_norm == miss_norm:
            return cand
    return None


def _audit_and_fix_dom_bindings(root: Path) -> dict[str, Any]:
    root = root.resolve()
    index = root / "index.html"
    if not index.exists():
        alt = root / "frontend" / "index.html"
        if alt.exists():
            index = alt
        else:
            return {"healthy": False, "issues": ["entry_point_missing:index.html"], "fixed": []}

    html = index.read_text(encoding="utf-8", errors="ignore")
    ids = set(re.findall(r"""id\s*=\s*["']([^"']+)["']""", html, flags=re.IGNORECASE))
    if not ids:
        return {"healthy": False, "issues": ["html_has_no_ids_for_binding"], "fixed": []}

    js_files: list[Path] = []
    for src in re.findall(r"""<script[^>]+src\s*=\s*["']([^"']+)["']""", html, flags=re.IGNORECASE):
        s = src.strip()
        if not s or re.match(r"^(https?:)?//", s) or s.startswith("data:") or s.startswith("#"):
            continue
        p = (index.parent / s.lstrip("./")).resolve()
        if p.exists() and p.suffix.lower() == ".js":
            js_files.append(p)

    if not js_files and (index.parent / "game.js").exists():
        js_files.append((index.parent / "game.js").resolve())

    fixed: list[str] = []
    issues: list[str] = []

    for js in js_files:
        try:
            txt = js.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        requested_ids = set(re.findall(r"""getElementById\(\s*["']([^"']+)["']\s*\)""", txt))
        requested_ids.update(re.findall(r"""querySelector\(\s*["']#([^"']+)["']\s*\)""", txt))
        changed = False
        for rid in sorted(requested_ids):
            if rid in ids:
                continue
            alias = _guess_id_alias(rid, ids)
            if alias is None:
                issues.append(f"missing_dom_id:{rid} in {js.name}")
                continue
            if alias != rid:
                txt2 = txt.replace(f'"{rid}"', f'"{alias}"').replace(f"'{rid}'", f"'{alias}'")
                if txt2 != txt:
                    txt = txt2
                    changed = True
                    fixed.append(f"{js.name}:{rid}->{alias}")
        if changed:
            js.write_text(txt, encoding="utf-8")

    return {"healthy": len(issues) == 0, "issues": issues, "fixed": fixed}


async def _start_preview_server(root: Path, framework: str, emit: Emit) -> str | None:
    normalized = StartupManager.normalize_framework(framework, None, root)
    ok, missing = StartupManager.preflight(normalized)
    if not ok:
        await emit("console_log", {"text": f"[preview] missing environment: {'; '.join(missing)}", "level": "error"})
        return None
    if normalized == "wechat_miniprogram":
        await emit("console_log", {"text": "[preview] WeChat MiniProgram preview requires DevTools.", "level": "error"})
        return None
    _ensure_entrypoint_alignment(root, normalized, max_depth=10)
    entry = _detect_entrypoint(root, normalized)
    if entry is None:
        _repair_workspace_layout(root, max_depth=10)
        _ensure_entrypoint_alignment(root, normalized, max_depth=10)
        entry = _detect_entrypoint(root, normalized)
    if entry is None:
        await emit("console_log", {"text": f"[preview] entry point missing for framework '{normalized}'.", "level": "error"})
        return None
    try:
        info = DevServerManager.start(
            workspace=str(root),
            framework=normalized,
            project_type=normalized,
            port=None,
            command=None,
        )
    except Exception as exc:
        await emit("console_log", {"text": f"[preview] failed to start devserver: {exc}", "level": "error"})
        return None
    health = await _await_preview_health(info.url)
    await emit(
        "console_log",
        {
            "text": f"[preview] {info.url} health={health.get('reason')}",
            "level": "success" if health.get("healthy") else "warning",
        },
    )
    await emit(
        "preview_health",
        {
            "url": info.url,
            "healthy": health.get("healthy") == True,
            "reason": health.get("reason"),
            "status_code": health.get("status_code"),
        },
    )
    return info.url if health.get("healthy") else None


async def _execute_autonomous_run(run_id: str, req: RunRequest) -> None:
    bus = get_event_bus()
    ExecutionStore.update(run_id, status=STATUS_RUNNING, stage="design", progress="Analyzing requirements...")
    
    # Log framework for debugging
    try:
        await asyncio.wait_for(
            bus.publish_event(
                run_id,
                {
                    "type": "console_log",
                    "payload": {"text": f"[config] framework={req.framework}, project_type={req.project_type}", "level": "info"},
                },
            ),
            timeout=float(os.getenv("REBOT_EVENT_EMIT_TIMEOUT_S", "2.5")),
        )
    except Exception:
        pass
    
    model_max_concurrency = _resolve_model_max_concurrency(
        requested=req.model_max_concurrency,
        model=req.model,
        base_url=req.base_url,
    )
    model = create_chat_model(
        ModelConfig(
            api_key=req.api_key,
            model=req.model,
            base_url=req.base_url,
            max_concurrency=model_max_concurrency,
        ),
        provider=req.provider,
    )
    workspace_root = Path(req.workspace)
    workspace_root.mkdir(parents=True, exist_ok=True)
    checkpoint_path = str(workspace_root / ".rebot" / "checkpoints" / f"{run_id}.json")
    ExecutionStore.update(
        run_id,
        metrics={
            "checkpoint_enabled": 1 if req.checkpoint_enabled else 0,
            "checkpoint_path": checkpoint_path,
            "resume_from_run_id": (req.resume_from_run_id or ""),
            "resume_checkpoint_stage": (req.resume_checkpoint_stage or ""),
        },
    )
    effective_task = req.task
    scheduler_framework = req.framework

    async def _emit(event_type: str, payload: Any) -> None:
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
            # Event bus is best-effort for UI observability.
            return

    try:
        if req.autogpt_agent_id:
            try:
                imported = import_agent_to_workspace(req.autogpt_agent_id, workspace_root)
                injected = (
                    f"AutoGPT imported profile: {imported.get('name')}\n"
                    f"Description:\n{imported.get('description')}\n\n"
                    f"Instructions:\n{imported.get('instructions')}\n"
                )
                effective_task = f"{req.task}\n\n[AutoGPT Profile]\n{injected}"
                await _emit(
                    "console_log",
                    {
                        "text": f"[autogpt] imported agent profile: {imported.get('name')} ({req.autogpt_agent_id})",
                        "level": "success",
                    },
                )
                if req.autogpt_workflow_enabled:
                    analysis = await execute_workflow_trace(
                        agent_id=req.autogpt_agent_id,
                        emit=_emit,
                        max_concurrency=max(1, int(req.multi_agent_workers or 10)),
                    )
                    workflow_hint = (
                        f"{analysis.summary}\n"
                        f"Parallel levels: {analysis.levels[:8]}\n"
                        f"Inferred files: {analysis.inferred_files[:120]}"
                    )
                    effective_task = f"{effective_task}\n\n[AutoGPT Workflow Trace]\n{workflow_hint}"
            except Exception as exc:
                await _emit("console_log", {"text": f"[autogpt] import failed: {exc}", "level": "warning"})

        req_fw = (req.framework or "").strip().lower()
        if req_fw in {"", "general"} and _is_game_task(effective_task):
            effective_task = _augment_game_task_for_production(effective_task)
            scheduler_framework = "html"
            await _emit(
                "console_log",
                {
                    "text": "[task_policy] general+game detected, forcing html production game contract",
                    "level": "info",
                },
            )

        await _emit("agent_thought", "Building repo map and loading experience memory...")
        repo_map_text = ""
        if req.repo_map:
            repo_builder = RepoMapBuilder(workspace_root)
            repo_map = repo_builder.build()
            repo_map_text = repo_builder.to_compact_text(repo_map)

        use_ast_context = os.getenv("REBOT_AST_CONTEXT_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
        ast_context_text = ""
        if use_ast_context:
            try:
                ast_indexer = ASTCodeIndexer(workspace_root, max_files=300, max_file_bytes=512_000)
                ast_index = ast_indexer.build(include_references=True)
                ast_context_text = ast_indexer.to_compact_text(ast_index, max_chars=12000)
                await _emit(
                    "console_log",
                    {
                        "text": f"[ast_context] files={ast_index.get('file_count', 0)} symbols={ast_index.get('symbol_count', 0)}",
                        "level": "default",
                    },
                )
            except Exception as exc:
                await _emit("console_log", {"text": f"[ast_context] build failed: {exc}", "level": "warning"})

        memory_hits: list[str] = []
        memory: ExperienceMemory | None = None
        failure_memory = FailureMemory(workspace_root / ".rebot" / "memory")
        if req.experience_memory:
            memory_timeout_s = max(3.0, float(os.getenv("REBOT_MEMORY_QUERY_TIMEOUT_S", "12")))
            try:
                def _init_and_query_memory() -> tuple[ExperienceMemory, list[str]]:
                    m = ExperienceMemory(workspace_root / ".rebot" / "memory")
                    hits = m.query(effective_task, top_k=4)
                    return m, hits

                memory, memory_hits = await asyncio.wait_for(
                    asyncio.to_thread(_init_and_query_memory),
                    timeout=memory_timeout_s,
                )
                await _emit(
                    "console_log",
                    {"text": f"[memory] backend={memory.mode}, hits={len(memory_hits)}", "level": "default"},
                )
            except asyncio.TimeoutError:
                memory = None
                memory_hits = []
                await _emit(
                    "console_log",
                    {"text": f"[memory] query timeout>{int(memory_timeout_s)}s, degraded to no-memory mode", "level": "warning"},
                )
            except Exception as exc:
                memory = None
                memory_hits = []
                await _emit("console_log", {"text": f"[memory] unavailable: {exc}", "level": "warning"})
        try:
            playbook_hits = failure_memory.query(
                query=effective_task,
                framework=str(req.framework or ""),
                top_k=3,
            )
        except Exception:
            playbook_hits = []
        if playbook_hits:
            memory_hits.extend(playbook_hits)
            await _emit(
                "console_log",
                {"text": f"[failure_playbook] loaded {len(playbook_hits)} hint(s)", "level": "info"},
            )

        loop = asyncio.get_running_loop()

        def _publish_event_threadsafe(event: dict[str, object]) -> None:
            try:
                asyncio.run_coroutine_threadsafe(bus.publish_event(run_id, event), loop)
            except Exception:
                pass

        def _resolve_role_model(role: str):
            overrides = req.role_model_overrides or {}
            role_cfg = overrides.get(role) if isinstance(overrides, dict) else None
            if not isinstance(role_cfg, dict):
                return req.provider, req.model, req.base_url, req.api_key, model_max_concurrency
            provider = str(role_cfg.get("provider") or req.provider or "").strip() or req.provider
            model_name = str(role_cfg.get("model") or req.model).strip() or req.model
            base_url = str(role_cfg.get("base_url") or req.base_url).strip() or req.base_url
            provider, base_url = normalize_llm_selection(
                provider=provider,
                model=model_name,
                base_url=base_url,
            )
            api_key = str(role_cfg.get("api_key") or req.api_key).strip() or req.api_key
            role_mc = role_cfg.get("max_concurrency")
            try:
                max_c = max(1, int(role_mc)) if role_mc is not None else model_max_concurrency
            except Exception:
                max_c = model_max_concurrency
            return provider, model_name, base_url, api_key, max_c

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
                    _publish_event_threadsafe({"type": "token", "payload": content})

            def _invoke_with_stream() -> Message:
                return model.invoke(messages, tools=[], stream_callback=_stream_cb)

            rsp = await asyncio.to_thread(_invoke_with_stream)
            # Use collected content if streaming worked, else fall back to response content
            if collected_content:
                return _strip_code_fences("".join(collected_content).strip())
            return _strip_code_fences(rsp.content if rsp else "")

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
                    _publish_event_threadsafe({"type": "token", "payload": content})

            def _invoke_with_stream() -> Message:
                return role_model.invoke(messages, tools=[], stream_callback=_stream_cb)

            rsp = await asyncio.to_thread(_invoke_with_stream)
            if collected_content:
                return _strip_code_fences("".join(collected_content).strip())
            return _strip_code_fences(rsp.content if rsp else "")

        resume_checkpoint: dict[str, Any] | None = None
        if (req.resume_from_run_id or "").strip():
            src = ExecutionStore.get(req.resume_from_run_id.strip())
            checkpoint_src = ""
            if src is not None:
                checkpoint_src = str(src.metrics.get("checkpoint_path") or "").strip()
            if checkpoint_src:
                p = Path(checkpoint_src)
                if p.exists():
                    try:
                        loaded = json.loads(p.read_text(encoding="utf-8"))
                        if isinstance(loaded, dict):
                            if (req.resume_checkpoint_stage or "").strip():
                                loaded["stage"] = req.resume_checkpoint_stage
                            resume_checkpoint = loaded
                            await _emit(
                                "console_log",
                                {
                                    "text": (
                                        f"[checkpoint] loaded from {req.resume_from_run_id} "
                                        f"stage={loaded.get('stage')}"
                                    ),
                                    "level": "info",
                                },
                            )
                    except Exception as exc:
                        await _emit(
                            "console_log",
                            {"text": f"[checkpoint] resume load failed: {exc}", "level": "warning"},
                        )

        if req.multi_agent:
            scheduler = MultiAgentScheduler(
                llm_call=_llm_call,
                role_llm_call=_role_llm_call,
                emit=_emit,
                max_workers=max(1, int(req.multi_agent_workers or model_max_concurrency)),
                retries=2,
                max_token_budget=req.max_token_budget,
                max_cost_budget=req.max_cost_budget,
                checkpoint_dir=(workspace_root / ".rebot" / "checkpoints") if req.checkpoint_enabled else None,
                run_id=run_id,
            )
            if resume_checkpoint is not None:
                plan_result = await scheduler.run_from_checkpoint(
                    task=effective_task,
                    repo_map=repo_map_text,
                    ast_context=ast_context_text,
                    memory_hints=memory_hits,
                    checkpoint=resume_checkpoint,
                    framework=scheduler_framework,
                )
            else:
                plan_result = await scheduler.run(
                    task=effective_task,
                    repo_map=repo_map_text,
                    ast_context=ast_context_text,
                    memory_hints=memory_hits,
                    framework=scheduler_framework,
                )
        else:
            await _emit("console_log", {"text": "[scheduler] multi_agent disabled, fallback single-agent path", "level": "warning"})
            scheduler = MultiAgentScheduler(
                llm_call=_llm_call,
                role_llm_call=_role_llm_call,
                emit=_emit,
                max_workers=1,
                retries=1,
                max_token_budget=req.max_token_budget,
                max_cost_budget=req.max_cost_budget,
                checkpoint_dir=(workspace_root / ".rebot" / "checkpoints") if req.checkpoint_enabled else None,
                run_id=run_id,
            )
            if resume_checkpoint is not None:
                plan_result = await scheduler.run_from_checkpoint(
                    task=effective_task,
                    repo_map=repo_map_text,
                    ast_context=ast_context_text,
                    memory_hints=memory_hits,
                    checkpoint=resume_checkpoint,
                    framework=scheduler_framework,
                )
            else:
                plan_result = await scheduler.run(
                    task=effective_task,
                    repo_map=repo_map_text,
                    ast_context=ast_context_text,
                    memory_hints=memory_hits,
                    framework=scheduler_framework,
                )

        ExecutionStore.update(run_id, stage="coding", progress="Writing files to workspace...")
        generated_paths: list[str] = []
        write_sem = asyncio.Semaphore(max(1, int(req.multi_agent_workers or model_max_concurrency)))
        write_lock = asyncio.Lock()

        async def _write_one(item: dict[str, Any]) -> None:
            rel_path = str(item.get("path") or "").strip().replace("\\", "/")
            file_content = str(item.get("content") or "")
            if not rel_path:
                return
            async with write_sem:
                path = _safe_join_workspace(workspace_root, rel_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(file_content, encoding="utf-8")
            async with write_lock:
                generated_paths.append(rel_path)
            await _emit("file_created", {"path": rel_path, "content": file_content})

        async def _apply_artifacts(result_obj: dict[str, Any]) -> list[str]:
            nonlocal generated_paths
            generated_paths = []
            artifacts_local = result_obj.get("artifacts") if isinstance(result_obj, dict) else None
            if not isinstance(artifacts_local, list):
                artifacts_local = []
            await asyncio.gather(*(_write_one(item) for item in artifacts_local if isinstance(item, dict)))
            return generated_paths

        runtime_blocking_issues: list[str] = []

        async def _post_apply_checks() -> str:
            nonlocal runtime_blocking_issues
            runtime_blocking_issues = []
            # Use user-selected framework if specified (not general), else infer from files.
            if req.framework and req.framework.strip().lower() not in {"general", ""}:
                fw = req.framework.strip().lower()
                await _emit("console_log", {"text": f"[framework] using user-selected: {fw}", "level": "info"})
            else:
                fw = _guess_framework_from_files(generated_paths)
                await _emit("console_log", {"text": f"[framework] inferred from files: {fw}", "level": "info"})
            await _initialize_framework_project(workspace_root, fw, _emit)
            align = _ensure_entrypoint_alignment(workspace_root, fw, max_depth=10)
            moved = align.get("moved") if isinstance(align, dict) else None
            if isinstance(moved, list) and moved:
                await _emit("console_log", {"text": f"[workspace] realigned {len(moved)} file(s) to workspace root", "level": "warning"})
            if fw == "html":
                audit = _audit_and_fix_html_runtime(workspace_root)
                for item in audit.get("fixed", []):
                    await _emit("console_log", {"text": f"[html_fix] {item}", "level": "default"})
                for item in audit.get("issues", []):
                    await _emit("console_log", {"text": f"[html_audit] {item}", "level": "warning"})
                dom_audit = _audit_and_fix_dom_bindings(workspace_root)
                for item in dom_audit.get("fixed", []):
                    await _emit("console_log", {"text": f"[dom_fix] {item}", "level": "default"})
                for item in dom_audit.get("issues", []):
                    await _emit("console_log", {"text": f"[dom_audit] {item}", "level": "warning"})
                issues = dom_audit.get("issues")
                if isinstance(issues, list):
                    runtime_blocking_issues.extend(str(x) for x in issues if str(x).strip())
            return fw

        async def _run_smoke_gate(fw: str) -> dict[str, Any]:
            await _emit("run_stage", {"stage": "smoke_check", "message": f"Running {fw} smoke checks..."})
            report = await asyncio.to_thread(
                run_framework_smoke_check,
                workspace=workspace_root,
                framework=fw,
            )
            if fw == "html" and runtime_blocking_issues:
                existing = report.get("blocking_issues")
                if not isinstance(existing, list):
                    existing = []
                existing.extend(f"dom_audit:{x}" for x in runtime_blocking_issues)
                report["blocking_issues"] = existing
                report["ok"] = False
                report["summary"] = f"failed:{'; '.join(existing[:6])}"
            level = "success" if report.get("ok") else "error"
            await _emit("console_log", {"text": f"[smoke_gate] {report.get('summary')}", "level": level})
            checks = report.get("checks")
            if isinstance(checks, list):
                for item in checks[:16]:
                    if not isinstance(item, dict):
                        continue
                    await _emit(
                        "console_log",
                        {
                            "text": f"[smoke_gate] {item.get('name')}: {'ok' if item.get('ok') else 'fail'}",
                            "level": "default" if item.get("ok") else "warning",
                        },
                    )
            return report

        await _apply_artifacts(plan_result)
        effective_framework = await _post_apply_checks()
        smoke_check_enabled = bool(req.smoke_check_enabled)
        smoke_rework_budget = max(0, min(int(req.smoke_rework_budget), 3))
        if smoke_check_enabled:
            smoke_gate = await _run_smoke_gate(effective_framework)
        else:
            smoke_gate = {
                "ok": True,
                "framework": effective_framework,
                "summary": "disabled",
                "checks": [],
                "blocking_issues": [],
            }
        smoke_attempt = 0
        while smoke_check_enabled and (smoke_gate.get("ok") is not True) and smoke_attempt < smoke_rework_budget:
            smoke_attempt += 1
            blocking = smoke_gate.get("blocking_issues")
            blocking_list = [str(x) for x in (list(blocking) if isinstance(blocking, list) else []) if str(x).strip()]
            failure_memory.add_case(
                query=effective_task,
                framework=effective_framework,
                issues=blocking_list,
                success=False,
                resolution=f"smoke_summary={smoke_gate.get('summary')}",
                metadata={"run_id": run_id, "stage": "smoke_gate", "attempt": smoke_attempt},
            )
            env_blockers = detect_environment_blockers(blocking_list)
            if env_blockers:
                env_text = "; ".join(env_blockers[:6])
                failure_memory.add_case(
                    query=effective_task,
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
                    "text": f"[smoke_gate] failed, triggering auto rework {smoke_attempt}/{smoke_rework_budget}",
                    "level": "warning",
                },
            )
            rework_task = build_smoke_rework_task(
                base_task=effective_task,
                framework=effective_framework,
                blocking_issues=blocking_list,
                attempt=smoke_attempt,
                budget=smoke_rework_budget,
                is_game=_is_game_task(effective_task),
            )
            plan_result = await scheduler.run(
                task=rework_task,
                repo_map=repo_map_text,
                ast_context=ast_context_text,
                memory_hints=memory_hits,
                framework=scheduler_framework,
            )
            await _apply_artifacts(plan_result)
            effective_framework = await _post_apply_checks()
            smoke_gate = await _run_smoke_gate(effective_framework)

        if smoke_check_enabled and smoke_gate.get("ok") is not True:
            failure_memory.add_case(
                query=effective_task,
                framework=effective_framework,
                issues=[str(x) for x in (smoke_gate.get("blocking_issues") or []) if str(x).strip()],
                success=False,
                resolution=f"smoke_summary={smoke_gate.get('summary')}",
                metadata={"run_id": run_id, "stage": "smoke_gate_final"},
            )
            raise RuntimeError(f"Smoke gate failed: {smoke_gate.get('summary')}")

        review_summary = str(plan_result.get("review") or "")
        if review_summary.strip():
            await _emit("assistant_message", review_summary)
            await _emit("console_log", {"text": f"[review] {review_summary[:400]}", "level": "default"})

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
                query=req.task,
                resolution=(
                    f"task={effective_task[:2000]}\n"
                ) + (
                    f"generated_files={len(generated_paths)}\n"
                    f"files={generated_paths[:60]}\n"
                    f"review={review_summary[:2000]}\n"
                    f"quality={quality_status}\n"
                    f"prd_total={prd_total}\n"
                    f"visual_total={visual_total}"
                ),
                metadata={"run_id": run_id, "provider": req.provider or "auto", "model": req.model},
            )
        failure_memory.add_case(
            query=effective_task,
            framework=effective_framework,
            issues=[str(x) for x in (smoke_gate.get("blocking_issues") or []) if str(x).strip()],
            success=True,
            resolution=(
                f"smoke_summary={smoke_gate.get('summary')}\n"
                f"review={review_summary[:900]}\n"
                f"quality={str((plan_result.get('quality_gate') or {}).get('final_status') or '')}"
            ),
            metadata={"run_id": run_id, "stage": "done"},
        )

        await _emit("console_log", {"text": "[preview] starting dev server...", "level": "info"})
        preview_url = await _start_preview_server(workspace_root, effective_framework, _emit)
        if preview_url is not None:
            await _emit("preview_ready", {"url": preview_url})

        result = {
            "project_id": req.project_id,
            "workspace": str(workspace_root),
            "files": generated_paths,
            "status": "completed",
            "preview_url": preview_url,
            "framework": effective_framework,
            "review": str(plan_result.get("review") or "") if isinstance(plan_result, dict) else "",
            "quality_gate": (plan_result.get("quality_gate") if isinstance(plan_result, dict) else None),
            "prd_score": (plan_result.get("prd_score") if isinstance(plan_result, dict) else None),
            "visual_score": (plan_result.get("visual_score") if isinstance(plan_result, dict) else None),
            "smoke_gate": smoke_gate,
            "budget": (plan_result.get("budget") if isinstance(plan_result, dict) else None),
        }
        if req.cache_key:
            cache.set(req.cache_key, result, ttl_s=req.cache_ttl_s)
        ExecutionStore.update(
            run_id,
            status=STATUS_FINISHED,
            stage="done",
            progress="Completed.",
            result=result,
        )
        await _emit("console_log", {"text": "Compiling...", "level": "default"})
        await _emit(
            "done",
            {
                "status": "completed",
                "run_id": run_id,
                "preview_url": preview_url,
                "workspace": str(workspace_root),
                "quality_gate": result.get("quality_gate"),
                "prd_score": result.get("prd_score"),
                "visual_score": result.get("visual_score"),
                "smoke_gate": result.get("smoke_gate"),
            },
        )
    except Exception as exc:
        try:
            fm = FailureMemory(workspace_root / ".rebot" / "memory")
            fm.add_case(
                query=effective_task if "effective_task" in locals() else req.task,
                framework=(effective_framework if "effective_framework" in locals() else str(req.framework or "")),
                issues=[str(exc)],
                success=False,
                resolution="run_exception",
                metadata={"run_id": run_id, "stage": "failed"},
            )
        except Exception:
            pass
        ExecutionStore.update(
            run_id,
            status=STATUS_FAILED,
            stage="failed",
            progress=str(exc),
            result={"error": str(exc), "code": "E_AUTONOMOUS_RUN_FAILED"},
        )
        await _emit("console_log", {"text": str(exc), "level": "error"})
        await _emit("done", {"status": "failed", "error": str(exc)})


def _template_market_root() -> Path:
    home = Path.home()
    root = (home / ".rebot" / "template_market").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _slugify_name(name: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", (name or "").strip())
    text = text.strip("-._")
    return text or f"template-{int(time.time())}"


def _safe_copytree(src: Path, dst: Path) -> None:
    ignore = shutil.ignore_patterns(
        ".git",
        ".idea",
        ".vscode",
        "__pycache__",
        ".dart_tool",
        "build",
        "node_modules",
        ".rebot",
    )
    shutil.copytree(src, dst, ignore=ignore)


def _load_template_item(path: Path) -> dict[str, Any] | None:
    meta_file = path / "template.json"
    project_dir = path / "project"
    if not meta_file.exists() or not project_dir.exists():
        return None
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(meta, dict):
        return None
    return {
        "id": str(meta.get("id") or path.name),
        "name": str(meta.get("name") or path.name),
        "description": str(meta.get("description") or ""),
        "framework": str(meta.get("framework") or "general"),
        "project_type": str(meta.get("project_type") or meta.get("framework") or "general"),
        "tags": list(meta.get("tags") or []),
        "created_at": str(meta.get("created_at") or ""),
        "updated_at": str(meta.get("updated_at") or ""),
        "project_path": str(project_dir),
        "template_path": str(path),
    }


@router.get("/templates/market")
async def list_template_market(q: str | None = None, limit: int = 200):
    root = _template_market_root()
    items: list[dict[str, Any]] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        item = _load_template_item(child)
        if item is None:
            continue
        items.append(item)
    items.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    query = (q or "").strip().lower()
    if query:
        items = [
            i for i in items
            if query in str(i.get("name") or "").lower()
            or query in str(i.get("description") or "").lower()
            or query in ",".join(str(t) for t in i.get("tags") or []).lower()
        ]
    return {"ok": True, "count": len(items[: max(1, min(limit, 500))]), "items": items[: max(1, min(limit, 500))]}


@router.post("/templates/market/save")
async def save_template_market(req: TemplateMarketSaveRequest):
    src = Path(req.workspace).expanduser().resolve()
    if not src.exists() or not src.is_dir():
        return {"ok": False, "error": "workspace_not_found"}
    root = _template_market_root()
    template_name = req.name.strip() or src.name
    slug = _slugify_name(template_name)
    template_id = f"{slug}-{int(time.time())}"
    target = root / template_id
    project_dst = target / "project"
    target.mkdir(parents=True, exist_ok=False)
    _safe_copytree(src, project_dst)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta = {
        "id": template_id,
        "name": template_name,
        "description": (req.description or "").strip(),
        "framework": (req.framework or "general").strip() or "general",
        "project_type": (req.project_type or req.framework or "general").strip() or "general",
        "tags": [str(t).strip() for t in (req.tags or []) if str(t).strip()],
        "source_workspace": str(src),
        "created_at": now,
        "updated_at": now,
    }
    (target / "template.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "template": _load_template_item(target)}


@router.post("/templates/market/import")
async def import_template_market(req: TemplateMarketImportRequest):
    src = Path(req.source_path).expanduser().resolve()
    if not src.exists():
        return {"ok": False, "error": "source_not_found"}
    root = _template_market_root()
    template_name = (req.name or src.stem or src.name).strip() or "imported-template"
    slug = _slugify_name(template_name)
    template_id = f"{slug}-{int(time.time())}"
    target = root / template_id
    project_dst = target / "project"
    target.mkdir(parents=True, exist_ok=False)
    if src.is_dir():
        _safe_copytree(src, project_dst)
    else:
        if src.suffix.lower() != ".zip":
            return {"ok": False, "error": "only_directory_or_zip_supported"}
        with tempfile.TemporaryDirectory(prefix="rebot_template_import_") as tmp:
            tmp_root = Path(tmp)
            with zipfile.ZipFile(src, "r") as zf:
                zf.extractall(tmp_root)
            children = [p for p in tmp_root.iterdir()]
            unpack_root = children[0] if len(children) == 1 and children[0].is_dir() else tmp_root
            _safe_copytree(unpack_root, project_dst)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta = {
        "id": template_id,
        "name": template_name,
        "description": (req.description or "").strip(),
        "framework": (req.framework or "general").strip() or "general",
        "project_type": (req.project_type or req.framework or "general").strip() or "general",
        "tags": [str(t).strip() for t in (req.tags or []) if str(t).strip()],
        "source_path": str(src),
        "created_at": now,
        "updated_at": now,
    }
    (target / "template.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "template": _load_template_item(target)}


@router.post("/templates/market/open")
async def open_template_market(req: TemplateMarketOpenRequest):
    root = _template_market_root()
    tpl_dir = (root / req.template_id).resolve()
    if not tpl_dir.exists() or not tpl_dir.is_dir():
        return {"ok": False, "error": "template_not_found"}
    item = _load_template_item(tpl_dir)
    if item is None:
        return {"ok": False, "error": "template_invalid"}
    src = Path(str(item["project_path"])).resolve()
    if not src.exists():
        return {"ok": False, "error": "template_project_missing"}

    name = (req.name or item.get("name") or tpl_dir.name).strip() or tpl_dir.name
    if req.destination and req.destination.strip():
        dst = Path(req.destination).expanduser().resolve()
    else:
        ws_root = (Path.cwd() / "workspace").resolve()
        ws_root.mkdir(parents=True, exist_ok=True)
        base = _slugify_name(name)
        dst = ws_root / base
        if dst.exists():
            idx = 2
            while (ws_root / f"{base}-{idx}").exists():
                idx += 1
            dst = ws_root / f"{base}-{idx}"
    if dst.exists() and any(dst.iterdir()):
        return {"ok": False, "error": f"destination_not_empty:{dst}"}
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    _safe_copytree(src, dst)
    return {
        "ok": True,
        "name": name,
        "workspace": str(dst),
        "framework": (req.framework or str(item.get("framework") or "general")).strip() or "general",
        "project_type": (req.project_type or str(item.get("project_type") or item.get("framework") or "general")).strip() or "general",
        "template_id": req.template_id,
    }


PLUGIN_ALLOWED_PERMISSIONS = {
    "fs.read",
    "fs.write",
    "git.read",
    "git.write",
    "net.http",
    "exec.command",
}
PLUGIN_ALLOWED_SIGNATURE_ALG = {"hmac-sha256"}


def _plugin_root() -> Path:
    root = (Path.home() / ".rebot" / "plugins").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _plugin_registry_file() -> Path:
    return _plugin_root() / "registry.json"


def _load_plugin_registry() -> dict[str, Any]:
    f = _plugin_registry_file()
    if not f.exists():
        return {"plugins": {}}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("plugins"), dict):
            return data
    except Exception:
        pass
    return {"plugins": {}}


def _save_plugin_registry(data: dict[str, Any]) -> None:
    f = _plugin_registry_file()
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _validate_plugin_manifest(manifest: dict[str, Any]) -> tuple[bool, str]:
    pid = str(manifest.get("id") or "").strip()
    name = str(manifest.get("name") or "").strip()
    version = str(manifest.get("version") or "").strip()
    if not pid:
        return False, "manifest_missing_id"
    if not name:
        return False, "manifest_missing_name"
    if not version:
        return False, "manifest_missing_version"
    perms_raw = manifest.get("permissions") or []
    if not isinstance(perms_raw, list):
        return False, "manifest_permissions_must_be_list"
    bad = [str(p) for p in perms_raw if str(p) not in PLUGIN_ALLOWED_PERMISSIONS]
    if bad:
        return False, f"manifest_permissions_invalid:{','.join(bad)}"
    sig_alg = str(manifest.get("signature_alg") or "").strip().lower()
    if sig_alg and sig_alg not in PLUGIN_ALLOWED_SIGNATURE_ALG:
        return False, f"manifest_signature_alg_unsupported:{sig_alg}"
    return True, ""


def _plugin_package_digest(package_root: Path) -> str:
    files: list[Path] = []
    for p in package_root.rglob("*"):
        if p.is_file():
            rel = p.relative_to(package_root).as_posix()
            if rel in {"plugin.json", "plugin.sig"}:
                continue
            files.append(p)
    files.sort(key=lambda x: x.relative_to(package_root).as_posix())
    hasher = hashlib.sha256()
    for p in files:
        rel = p.relative_to(package_root).as_posix().encode("utf-8")
        hasher.update(rel)
        hasher.update(b"\n")
        hasher.update(p.read_bytes())
        hasher.update(b"\n")
    return hasher.hexdigest()


def _signature_payload(*, plugin_id: str, version: str, digest: str) -> str:
    return f"{plugin_id}\n{version}\n{digest}"


def _verify_plugin_signature(manifest: dict[str, Any], package_root: Path) -> tuple[bool, str, str]:
    plugin_id = str(manifest.get("id") or "").strip()
    version = str(manifest.get("version") or "").strip()
    digest = _plugin_package_digest(package_root)
    sig = str(manifest.get("signature") or "").strip()
    alg = str(manifest.get("signature_alg") or "").strip().lower() or "hmac-sha256"
    if not sig:
        return True, "unsigned", digest
    if alg != "hmac-sha256":
        return False, "signature_alg_unsupported", digest
    key = (os.getenv("REBOT_PLUGIN_SIGNING_KEY") or "").encode("utf-8")
    if not key:
        return False, "signature_key_missing", digest
    payload = _signature_payload(plugin_id=plugin_id, version=version, digest=digest).encode("utf-8")
    expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False, "signature_mismatch", digest
    return True, "verified", digest


def _locate_plugin_package(src: Path) -> tuple[Path, dict[str, Any]]:
    if src.is_dir():
        manifest_path = src / "plugin.json"
        if not manifest_path.exists():
            children = [p for p in src.iterdir() if p.is_dir()]
            for c in children:
                candidate = c / "plugin.json"
                if candidate.exists():
                    manifest_path = candidate
                    src = c
                    break
        if not manifest_path.exists():
            raise ValueError("plugin_manifest_not_found")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("plugin_manifest_invalid_json")
        return src, manifest
    if src.suffix.lower() != ".zip":
        raise ValueError("plugin_source_must_be_dir_or_zip")
    with tempfile.TemporaryDirectory(prefix="rebot_plugin_unpack_") as tmp:
        tmp_root = Path(tmp)
        with zipfile.ZipFile(src, "r") as zf:
            zf.extractall(tmp_root)
        candidates = [tmp_root] + [p for p in tmp_root.iterdir() if p.is_dir()]
        for c in candidates:
            manifest_path = c / "plugin.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if not isinstance(manifest, dict):
                    raise ValueError("plugin_manifest_invalid_json")
                persistent = (_plugin_root() / "_tmp_unpack" / f"{int(time.time())}_{c.name}").resolve()
                if persistent.exists():
                    shutil.rmtree(persistent, ignore_errors=True)
                persistent.parent.mkdir(parents=True, exist_ok=True)
                _safe_copytree(c, persistent)
                return persistent, manifest
    raise ValueError("plugin_manifest_not_found_in_zip")


def _plugin_public_record(item: dict[str, Any]) -> dict[str, Any]:
    out = {
        "id": str(item.get("id") or ""),
        "name": str(item.get("name") or ""),
        "version": str(item.get("version") or ""),
        "description": str(item.get("description") or ""),
        "enabled": bool(item.get("enabled", True)),
        "permissions": list(item.get("permissions") or []),
        "index_status": str(item.get("index_status") or "ok"),
        "signature_alg": str(item.get("signature_alg") or ""),
        "digest": str(item.get("digest") or ""),
        "installed_at": str(item.get("installed_at") or ""),
        "updated_at": str(item.get("updated_at") or ""),
        "current_path": str(item.get("current_path") or ""),
    }
    versions = item.get("versions")
    if isinstance(versions, list):
        out["versions"] = versions[-20:]
    return out


def _install_or_upgrade_plugin(src_path: str, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    src = Path(src_path).expanduser().resolve()
    if not src.exists():
        raise ValueError("plugin_source_not_found")
    package_root, manifest = _locate_plugin_package(src)
    ok, err = _validate_plugin_manifest(manifest)
    if not ok:
        raise ValueError(err)
    pid = str(manifest.get("id") or "").strip()
    name = str(manifest.get("name") or "").strip()
    version = str(manifest.get("version") or "").strip()
    description = str(manifest.get("description") or "").strip()
    permissions = [str(p) for p in (manifest.get("permissions") or [])]
    sig_ok, sig_status, digest = _verify_plugin_signature(manifest, package_root)
    if not sig_ok:
        raise ValueError(f"plugin_signature_invalid:{sig_status}")

    plugins_dir = _plugin_root() / "installed" / pid
    versions_dir = plugins_dir / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    version_dir_name = f"{version}-{ts}"
    version_dir = versions_dir / version_dir_name
    if version_dir.exists():
        raise ValueError("plugin_version_conflict")
    _safe_copytree(package_root, version_dir)

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    previous_versions: list[dict[str, Any]] = []
    enabled = True
    if existing is not None:
        pv = existing.get("versions")
        if isinstance(pv, list):
            previous_versions = list(pv)
        enabled = bool(existing.get("enabled", True))
    previous_versions.append(
        {
            "version": version,
            "installed_at": now,
            "path": str(version_dir),
        }
    )
    return {
        "id": pid,
        "name": name,
        "version": version,
        "description": description,
        "enabled": enabled,
        "permissions": permissions,
        "index_status": sig_status if sig_status else "ok",
        "signature_alg": str(manifest.get("signature_alg") or "hmac-sha256"),
        "digest": digest,
        "installed_at": (existing or {}).get("installed_at") or now,
        "updated_at": now,
        "current_path": str(version_dir),
        "versions": previous_versions,
    }


@router.get("/plugins/installed")
async def list_plugins_installed():
    registry = _load_plugin_registry()
    plugins = registry.get("plugins")
    if not isinstance(plugins, dict):
        plugins = {}
    items = [_plugin_public_record(v) for v in plugins.values() if isinstance(v, dict)]
    items.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    return {"ok": True, "count": len(items), "plugins": items}


@router.post("/plugins/install")
async def install_plugin(req: PluginInstallRequest):
    registry = _load_plugin_registry()
    plugins = registry.get("plugins")
    if not isinstance(plugins, dict):
        plugins = {}
        registry["plugins"] = plugins
    item = _install_or_upgrade_plugin(req.source_path, existing=None)
    pid = item["id"]
    if pid in plugins:
        return {"ok": False, "error": "plugin_already_installed"}
    plugins[pid] = item
    _save_plugin_registry(registry)
    return {"ok": True, "plugin": _plugin_public_record(item)}


@router.post("/plugins/upgrade")
async def upgrade_plugin(req: PluginUpgradeRequest):
    registry = _load_plugin_registry()
    plugins = registry.get("plugins")
    if not isinstance(plugins, dict):
        return {"ok": False, "error": "plugin_registry_invalid"}
    existing = plugins.get(req.plugin_id)
    if not isinstance(existing, dict):
        return {"ok": False, "error": "plugin_not_found"}
    item = _install_or_upgrade_plugin(req.source_path, existing=existing)
    if str(item.get("id") or "") != req.plugin_id:
        return {"ok": False, "error": "plugin_id_mismatch"}
    plugins[req.plugin_id] = item
    _save_plugin_registry(registry)
    return {"ok": True, "plugin": _plugin_public_record(item)}


@router.post("/plugins/rollback")
async def rollback_plugin(req: PluginRollbackRequest):
    registry = _load_plugin_registry()
    plugins = registry.get("plugins")
    if not isinstance(plugins, dict):
        return {"ok": False, "error": "plugin_registry_invalid"}
    existing = plugins.get(req.plugin_id)
    if not isinstance(existing, dict):
        return {"ok": False, "error": "plugin_not_found"}
    versions = existing.get("versions")
    if not isinstance(versions, list) or len(versions) < 2:
        return {"ok": False, "error": "plugin_no_previous_version"}
    versions.pop()
    prev = versions[-1]
    prev_path = Path(str(prev.get("path") or "")).expanduser().resolve()
    if not prev_path.exists() or not prev_path.is_dir():
        return {"ok": False, "error": "plugin_previous_version_missing"}
    existing["version"] = str(prev.get("version") or existing.get("version") or "")
    existing["current_path"] = str(prev_path)
    existing["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    existing["versions"] = versions
    plugins[req.plugin_id] = existing
    _save_plugin_registry(registry)
    return {"ok": True, "plugin": _plugin_public_record(existing)}


@router.post("/plugins/toggle")
async def toggle_plugin(req: PluginToggleRequest):
    registry = _load_plugin_registry()
    plugins = registry.get("plugins")
    if not isinstance(plugins, dict):
        return {"ok": False, "error": "plugin_registry_invalid"}
    existing = plugins.get(req.plugin_id)
    if not isinstance(existing, dict):
        return {"ok": False, "error": "plugin_not_found"}
    existing["enabled"] = bool(req.enabled)
    existing["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    plugins[req.plugin_id] = existing
    _save_plugin_registry(registry)
    return {"ok": True, "plugin": _plugin_public_record(existing)}


def _plugin_get_installed(plugin_id: str) -> dict[str, Any] | None:
    registry = _load_plugin_registry()
    plugins = registry.get("plugins")
    if not isinstance(plugins, dict):
        return None
    item = plugins.get(plugin_id)
    if not isinstance(item, dict):
        return None
    return item


def _plugin_require_permission(plugin: dict[str, Any], permission: str) -> None:
    perms = plugin.get("permissions")
    if not isinstance(perms, list):
        raise PermissionError("plugin_permissions_missing")
    if permission not in {str(p) for p in perms}:
        raise PermissionError(f"plugin_permission_denied:{permission}")


def _plugin_workspace_root(workspace: str | None) -> Path:
    ws = str(workspace or "").strip()
    if ws:
        root = Path(ws).expanduser().resolve()
    else:
        root = Path.cwd().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _plugin_require_git_repo(workspace_root: Path) -> None:
    if not (workspace_root / ".git").exists():
        raise ValueError("git_repo_not_found")


@router.post("/plugins/execute")
async def execute_plugin(req: PluginExecutionRequest):
    plugin = _plugin_get_installed(req.plugin_id)
    if plugin is None:
        return {"ok": False, "error": "plugin_not_found"}
    if not bool(plugin.get("enabled", True)):
        return {"ok": False, "error": "plugin_disabled"}

    op = str(req.operation or "").strip().lower()
    args = req.args if isinstance(req.args, dict) else {}
    workspace_root = _plugin_workspace_root(req.workspace)

    try:
        if op == "fs.read":
            _plugin_require_permission(plugin, "fs.read")
            rel = str(args.get("path") or "").strip().replace("\\", "/")
            if not rel:
                return {"ok": False, "error": "path_required"}
            target = _safe_join_workspace(workspace_root, rel)
            if not target.exists() or not target.is_file():
                return {"ok": False, "error": "file_not_found"}
            content = target.read_text(encoding="utf-8", errors="ignore")
            return {"ok": True, "operation": op, "path": rel, "content": content[:1_000_000]}

        if op == "fs.write":
            _plugin_require_permission(plugin, "fs.write")
            rel = str(args.get("path") or "").strip().replace("\\", "/")
            content = str(args.get("content") or "")
            if not rel:
                return {"ok": False, "error": "path_required"}
            target = _safe_join_workspace(workspace_root, rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {"ok": True, "operation": op, "path": rel, "bytes": len(content.encode("utf-8"))}

        if op == "net.http_get":
            _plugin_require_permission(plugin, "net.http")
            url = str(args.get("url") or "").strip()
            if not url:
                return {"ok": False, "error": "url_required"}
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"}:
                return {"ok": False, "error": "url_scheme_not_allowed"}
            timeout = max(1, min(int(args.get("timeout_s") or 20), 120))

            def _do_get() -> dict[str, Any]:
                req_obj = urllib.request.Request(url=url, method="GET")
                with urllib.request.urlopen(req_obj, timeout=timeout) as resp:
                    body = resp.read(1_000_000)
                    try:
                        text = body.decode("utf-8", errors="ignore")
                    except Exception:
                        text = ""
                    return {
                        "status": int(getattr(resp, "status", 200)),
                        "headers": dict(resp.headers.items()),
                        "body": text,
                    }

            out = await asyncio.to_thread(_do_get)
            return {"ok": True, "operation": op, "response": out}

        if op == "exec.command":
            _plugin_require_permission(plugin, "exec.command")
            cmd_raw = args.get("command")
            if isinstance(cmd_raw, list):
                cmd = [str(x) for x in cmd_raw if str(x).strip()]
            else:
                cmd = split_command(str(cmd_raw or ""))
            if not cmd:
                return {"ok": False, "error": "command_required"}
            timeout = max(1, min(int(args.get("timeout_s") or 60), 600))
            proc = await asyncio.to_thread(
                run_checked,
                cmd,
                cwd=workspace_root,
                timeout=timeout,
                capture_output=True,
                text=True,
            )
            return {
                "ok": True,
                "operation": op,
                "returncode": int(proc.returncode),
                "stdout": str(proc.stdout or "")[-20000:],
                "stderr": str(proc.stderr or "")[-20000:],
            }

        if op == "git.status":
            _plugin_require_permission(plugin, "git.read")
            _plugin_require_git_repo(workspace_root)
            proc = await asyncio.to_thread(
                run_checked,
                ["git", "status", "--porcelain=2", "--branch"],
                cwd=workspace_root,
                timeout=30,
                capture_output=True,
                text=True,
            )
            return {
                "ok": True,
                "operation": op,
                "returncode": int(proc.returncode),
                "stdout": str(proc.stdout or "")[-20000:],
                "stderr": str(proc.stderr or "")[-20000:],
            }

        if op == "git.diff":
            _plugin_require_permission(plugin, "git.read")
            _plugin_require_git_repo(workspace_root)
            staged = bool(args.get("staged", False))
            path = str(args.get("path") or "").strip()
            cmd = ["git", "diff"]
            if staged:
                cmd.append("--staged")
            if path:
                cmd += ["--", path]
            proc = await asyncio.to_thread(
                run_checked,
                cmd,
                cwd=workspace_root,
                timeout=30,
                capture_output=True,
                text=True,
            )
            return {
                "ok": True,
                "operation": op,
                "returncode": int(proc.returncode),
                "diff": str(proc.stdout or "")[-200000:],
                "stderr": str(proc.stderr or "")[-20000:],
            }

        if op == "git.stage":
            _plugin_require_permission(plugin, "git.write")
            _plugin_require_git_repo(workspace_root)
            paths_raw = args.get("paths")
            paths: list[str] = []
            if isinstance(paths_raw, list):
                for p in paths_raw:
                    ps = str(p or "").strip()
                    if ps:
                        paths.append(ps)
            if not paths:
                paths = ["."]
            cmd = ["git", "add", "--"] + paths
            proc = await asyncio.to_thread(
                run_checked,
                cmd,
                cwd=workspace_root,
                timeout=60,
                capture_output=True,
                text=True,
            )
            return {
                "ok": True,
                "operation": op,
                "returncode": int(proc.returncode),
                "stdout": str(proc.stdout or "")[-20000:],
                "stderr": str(proc.stderr or "")[-20000:],
            }

        if op == "git.commit":
            _plugin_require_permission(plugin, "git.write")
            _plugin_require_git_repo(workspace_root)
            msg = str(args.get("message") or "").strip()
            if not msg:
                return {"ok": False, "error": "commit_message_required"}
            proc = await asyncio.to_thread(
                run_checked,
                ["git", "commit", "-m", msg],
                cwd=workspace_root,
                timeout=60,
                capture_output=True,
                text=True,
            )
            return {
                "ok": True,
                "operation": op,
                "returncode": int(proc.returncode),
                "stdout": str(proc.stdout or "")[-20000:],
                "stderr": str(proc.stderr or "")[-20000:],
            }

        return {"ok": False, "error": f"unsupported_operation:{op}"}
    except PermissionError as exc:
        return {"ok": False, "error": str(exc)}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": f"net_error:{exc}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "command_timeout"}
    except Exception as exc:
        return {"ok": False, "error": f"plugin_execute_failed:{exc}"}


@router.get("/plugins/sdk/template")
async def plugin_sdk_template():
    return {
        "ok": True,
        "files": {
            "plugin.json": {
                "id": "my.plugin.id",
                "name": "My Plugin",
                "version": "0.1.0",
                "description": "Plugin description",
                "permissions": ["fs.read"],
                "entry": "main.py",
                "signature_alg": "hmac-sha256",
                "signature": "",
            },
            "main.py": (
                "def run(context):\n"
                "    op = context.get('operation', '')\n"
                "    args = context.get('args', {})\n"
                "    return {'ok': True, 'operation': op, 'args': args}\n"
            ),
            "sign_plugin.ps1": (
                "$ErrorActionPreference='Stop'\n"
                "$root = Split-Path -Parent $MyInvocation.MyCommand.Path\n"
                "$manifestPath = Join-Path $root 'plugin.json'\n"
                "$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json\n"
                "$files = Get-ChildItem $root -Recurse -File | Where-Object { $_.Name -notin @('plugin.json','plugin.sig') } | Sort-Object FullName\n"
                "$sha = [System.Security.Cryptography.SHA256]::Create()\n"
                "$ms = New-Object System.IO.MemoryStream\n"
                "foreach ($f in $files) {\n"
                "  $rel = $f.FullName.Substring($root.Length + 1).Replace('\\\\','/')\n"
                "  $line = [System.Text.Encoding]::UTF8.GetBytes($rel + \"`n\")\n"
                "  $ms.Write($line,0,$line.Length)\n"
                "  $bytes = [System.IO.File]::ReadAllBytes($f.FullName)\n"
                "  $ms.Write($bytes,0,$bytes.Length)\n"
                "  $nl = [System.Text.Encoding]::UTF8.GetBytes(\"`n\")\n"
                "  $ms.Write($nl,0,$nl.Length)\n"
                "}\n"
                "$ms.Position = 0\n"
                "$digestBytes = $sha.ComputeHash($ms)\n"
                "$digest = -join ($digestBytes | ForEach-Object { $_.ToString('x2') })\n"
                "$key = $env:REBOT_PLUGIN_SIGNING_KEY\n"
                "if ([string]::IsNullOrWhiteSpace($key)) { throw 'REBOT_PLUGIN_SIGNING_KEY missing' }\n"
                "$payload = \"$($manifest.id)`n$($manifest.version)`n$digest\"\n"
                "$h = New-Object System.Security.Cryptography.HMACSHA256 ([System.Text.Encoding]::UTF8.GetBytes($key))\n"
                "$sigBytes = $h.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($payload))\n"
                "$sig = -join ($sigBytes | ForEach-Object { $_.ToString('x2') })\n"
                "$manifest.signature_alg = 'hmac-sha256'\n"
                "$manifest.signature = $sig\n"
                "$manifest | ConvertTo-Json -Depth 8 | Set-Content $manifestPath -Encoding UTF8\n"
                "Write-Host \"Signed. digest=$digest\"\n"
            ),
        },
    }


@router.post("/plugins/sdk/init")
async def plugin_sdk_init(req: PluginSdkInitRequest):
    dst = Path(req.destination).expanduser().resolve()
    if dst.exists() and any(dst.iterdir()):
        return {"ok": False, "error": f"destination_not_empty:{dst}"}
    dst.mkdir(parents=True, exist_ok=True)
    perms = [str(p).strip() for p in (req.permissions or []) if str(p).strip()]
    invalid = [p for p in perms if p not in PLUGIN_ALLOWED_PERMISSIONS]
    if invalid:
        return {"ok": False, "error": f"permissions_invalid:{','.join(invalid)}"}
    manifest = {
        "id": req.plugin_id.strip(),
        "name": req.name.strip(),
        "version": req.version.strip() or "0.1.0",
        "description": req.description.strip(),
        "permissions": perms,
        "entry": "main.py",
        "signature_alg": "hmac-sha256",
        "signature": "",
    }
    (dst / "plugin.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (dst / "main.py").write_text(
        (
            "def run(context):\n"
            "    operation = context.get('operation', '')\n"
            "    args = context.get('args', {})\n"
            "    return {'ok': True, 'operation': operation, 'args': args}\n"
        ),
        encoding="utf-8",
    )
    tmpl = await plugin_sdk_template()
    sign_script = str((tmpl.get("files") or {}).get("sign_plugin.ps1") or "")
    (dst / "sign_plugin.ps1").write_text(sign_script, encoding="utf-8")
    (dst / "README.md").write_text(
        (
            f"# {req.name.strip() or req.plugin_id.strip()}\n\n"
            "## Build\n"
            "1. Edit `plugin.json` permissions/metadata.\n"
            "2. Implement logic in `main.py`.\n"
            "3. Set env `REBOT_PLUGIN_SIGNING_KEY`.\n"
            "4. Run `./sign_plugin.ps1`.\n"
            "5. Install from Plugin Market.\n"
        ),
        encoding="utf-8",
    )
    return {"ok": True, "destination": str(dst), "plugin_id": req.plugin_id.strip()}


@router.post("/projects/clone")
async def clone_project(req: ProjectCloneRequest):
    started_at = time.perf_counter()
    status = "error"
    repo_url = (req.repo_url or "").strip()
    if not repo_url:
        status = "bad_request"
        observe_operation("project_clone", status, time.perf_counter() - started_at)
        return {"ok": False, "error": "repo_url is required"}

    def _guess_name(url: str) -> str:
        parsed = urlparse(url)
        path = (parsed.path or url).strip().rstrip("/")
        name = path.split("/")[-1] if path else "project"
        if name.endswith(".git"):
            name = name[:-4]
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-._")
        return name or "project"

    target = (req.destination or "").strip()
    if target:
        dst = Path(target).expanduser().resolve()
    else:
        root = (Path.cwd() / "workspace").resolve()
        root.mkdir(parents=True, exist_ok=True)
        name = _guess_name(repo_url)
        dst = (root / name).resolve()
        if dst.exists():
            suffix = 2
            while (root / f"{name}-{suffix}").exists():
                suffix += 1
            dst = (root / f"{name}-{suffix}").resolve()

    if dst.exists():
        try:
            has_files = any(dst.iterdir())
        except Exception:
            has_files = True
        if has_files:
            status = "destination_not_empty"
            observe_operation("project_clone", status, time.perf_counter() - started_at)
            return {"ok": False, "error": f"destination_not_empty:{dst}"}
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["git", "clone"]
    branch = (req.branch or "").strip()
    if branch:
        cmd += ["--branch", branch]
    depth = int(req.depth) if int(req.depth) > 0 else 1
    cmd += ["--depth", str(depth), repo_url, str(dst)]

    try:
        proc = await asyncio.to_thread(
            run_checked,
            cmd,
            cwd=dst.parent,
            timeout=600,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        status = "git_not_found"
        observe_operation("project_clone", status, time.perf_counter() - started_at)
        return {"ok": False, "error": "git_not_found"}
    except ValueError as exc:
        status = "validation_error"
        observe_operation("project_clone", status, time.perf_counter() - started_at)
        return {"ok": False, "error": str(exc)}
    except subprocess.TimeoutExpired:
        status = "clone_timeout"
        observe_operation("project_clone", status, time.perf_counter() - started_at)
        return {"ok": False, "error": "clone_timeout"}

    if proc.returncode != 0:
        status = "clone_failed"
        observe_operation("project_clone", status, time.perf_counter() - started_at)
        err = (proc.stderr or proc.stdout or "git clone failed").strip()
        return {"ok": False, "error": err}

    status = "ok"
    observe_operation("project_clone", status, time.perf_counter() - started_at)
    logger.info(
        "project_clone_ok",
        extra={"event": "project_clone_ok", "workspace": str(dst), "branch": branch or "default"},
    )
    return {
        "ok": True,
        "name": dst.name,
        "workspace": str(dst),
        "stdout": (proc.stdout or "").strip()[-2000:],
    }


@router.post("/llm/probe")
async def llm_probe(req: LlmProbeRequest):
    started_at = time.perf_counter()
    status = "error"
    try:
        model = create_chat_model(
            ModelConfig(
                api_key=req.api_key,
                model=req.model,
                base_url=req.base_url,
                timeout_s=max(5.0, float(req.timeout_s)),
                max_concurrency=1,
            ),
            provider=req.provider,
        )
        messages = [
            Message(role="system", content="You are a connectivity probe."),
            Message(role="user", content=req.prompt),
        ]
        rsp = await asyncio.to_thread(model.invoke, messages, tools=[])
        text = (getattr(rsp, "content", "") or "").strip()
        status = "ok"
        observe_operation("llm_probe", status, time.perf_counter() - started_at)
        return {
            "ok": True,
            "provider": req.provider or "auto",
            "model": req.model,
            "base_url": req.base_url,
            "response": text[:800],
        }
    except Exception as exc:
        status = "failed"
        observe_operation("llm_probe", status, time.perf_counter() - started_at)
        return {
            "ok": False,
            "provider": req.provider or "auto",
            "model": req.model,
            "base_url": req.base_url,
            "error": str(exc),
        }


@router.get("/autogpt/catalog")
async def autogpt_catalog(limit: int = 100):
    agents = autogpt_list_agents(limit=max(1, min(limit, 1000)))
    return {
        "count": len(agents),
        "agents": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "description": a.description,
                "source_path": a.source_path,
            }
            for a in agents
        ],
    }


@router.post("/autogpt/import")
async def autogpt_import(req: AutoGPTImportRequest):
    ws = Path(req.workspace).resolve()
    try:
        payload = import_agent_to_workspace(req.agent_id, ws)
        return {"ok": True, "workspace": str(ws), "agent": payload}
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"error": "autogpt_import_failed", "message": str(exc)}) from exc


@router.post("/autogpt/workflow/analyze")
async def autogpt_workflow_analyze(req: AutoGPTWorkflowAnalyzeRequest):
    try:
        a = analyze_agent_workflow(req.agent_id)
        return {
            "agent_id": a.agent_id,
            "name": a.name,
            "node_count": a.node_count,
            "edge_count": a.edge_count,
            "levels": a.levels,
            "inferred_files": a.inferred_files,
            "summary": a.summary,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"error": "autogpt_workflow_analyze_failed", "message": str(exc)}) from exc


@router.post("/workflow/execute", response_model=ExecuteResponse)
async def execute_workflow(req: WorkflowExecuteRequest):
    started_at = time.perf_counter()
    request_key = (
        f"workflow:{req.provider}:{req.model}:{req.base_url}:{req.workspace}:"
        f"{len(req.workflow.nodes)}:{len(req.workflow.edges)}"
    )
    existing = ExecutionStore.find_active_by_request_key(request_key)
    if existing is not None:
        observe_operation("workflow_execute", "deduplicated", time.perf_counter() - started_at)
        return ExecuteResponse(run_id=existing.run_id)
    record = ExecutionStore.create()
    ExecutionStore.update(
        record.run_id,
        metrics={"request_key": request_key, "job_type": "workflow"},
        status=STATUS_QUEUED,
        stage=STATUS_QUEUED,
        progress="Task queued.",
    )
    queue = get_task_queue()
    cache_key = req.cache_key or f"workflow:{req.provider}:{req.model}:{req.base_url}:{req.workspace}"
    cached = cache.get(cache_key)
    if cached:
        ExecutionStore.update(record.run_id, status="finished", result=cached)
        bus = get_event_bus()
        await bus.publish(record.run_id, [{"type": "cache_hit", "payload": cached}])
        observe_operation("workflow_execute", "cache_hit", time.perf_counter() - started_at)
        return ExecuteResponse(run_id=record.run_id)
    payload = req.model_dump()
    payload["cache_key"] = cache_key
    payload["job_type"] = "workflow"
    if queue is None:
        asyncio.create_task(_run_workflow_execution(record.run_id, req, cache_key))
    else:
        await queue.enqueue(record.run_id, payload)
    observe_operation("workflow_execute", "queued", time.perf_counter() - started_at)
    logger.info("workflow_execute_queued", extra={"event": "workflow_execute_queued", "run_id": record.run_id})
    return ExecuteResponse(run_id=record.run_id)


@router.post("/generate", response_model=ExecuteResponse)
async def generate(req: GenerateRequest):
    started_at = time.perf_counter()
    request_key = (
        f"generate:{req.provider}:{req.model}:{req.base_url}:{req.workspace}:"
        f"{req.requirement}:{req.language}:{','.join(req.platforms)}"
    )
    existing = ExecutionStore.find_active_by_request_key(request_key)
    if existing is not None:
        observe_operation("generate", "deduplicated", time.perf_counter() - started_at)
        return ExecuteResponse(run_id=existing.run_id)
    record = ExecutionStore.create()
    ExecutionStore.update(
        record.run_id,
        metrics={"request_key": request_key, "job_type": "generate"},
        status=STATUS_QUEUED,
        stage=STATUS_QUEUED,
        progress="Task queued.",
    )
    observe_operation("generate", "queued", time.perf_counter() - started_at)
    logger.info("generate_queued", extra={"event": "generate_queued", "run_id": record.run_id, "language": req.language})
    queue = get_task_queue()
    cache_key = (
        req.cache_key
        or f"generate:{req.provider}:{req.model}:{req.base_url}:{req.workspace}:{req.requirement}"
    )
    cached = cache.get(cache_key)
    if cached:
        ExecutionStore.update(record.run_id, status="finished", result=cached)
        bus = get_event_bus()
        await bus.publish(record.run_id, [{"type": "cache_hit", "payload": cached}])
        observe_operation("generate", "cache_hit", time.perf_counter() - started_at)
        return ExecuteResponse(run_id=record.run_id)
    payload = req.model_dump()
    payload["cache_key"] = cache_key
    payload["job_type"] = "generate"
    if queue is None:
        asyncio.create_task(_run_generate(record.run_id, req, cache_key))
    else:
        await queue.enqueue(record.run_id, payload)
    return ExecuteResponse(run_id=record.run_id)


async def _run_execution(run_id: str, req: ExecuteRequest, cache_key: str) -> None:
    ExecutionStore.update(run_id, status=STATUS_RUNNING, stage="agent", progress="Running coding agent...")
    model_max_concurrency = _resolve_model_max_concurrency(
        requested=req.model_max_concurrency,
        model=req.model,
        base_url=req.base_url,
    )
    model = create_chat_model(
        ModelConfig(
            api_key=req.api_key,
            model=req.model,
            base_url=req.base_url,
            max_concurrency=model_max_concurrency,
        ),
        provider=req.provider,
    )
    agent = CodingAgent(model=model, workspace_root=Path(req.workspace), review_mode=req.review_mode)
    events: list[dict] = []
    bus = get_event_bus()
    native_metrics: dict[str, Any] = {}
    loop = asyncio.get_running_loop()

    def _publish_event_threadsafe(event: dict[str, Any]) -> None:
        try:
            asyncio.run_coroutine_threadsafe(bus.publish_event(run_id, event), loop)
        except Exception:
            pass

    def stream_cb(chunk):
        ExecutionStore.update(run_id, status=STATUS_STREAMING, stage="streaming", progress="Streaming model output...")
        _publish_event_threadsafe({"type": "token", "payload": chunk.content})

    def sink(event: dict[str, Any]) -> None:
        _publish_event_threadsafe(event)

    callbacks = TraceCollector(run_id=run_id, sink=sink, events=events)

    if req.metagpt_native:
        await bus.publish_event(
            run_id,
            {"type": "run_stage", "payload": {"stage": "metagpt_native", "message": "Running native MetaGPT..."}},
        )
        try:
            from rebot.auto.metagpt_native_bridge import run_native_metagpt

            native = await asyncio.to_thread(
                run_native_metagpt,
                requirement=req.task,
                workspace=req.workspace,
                api_key=req.api_key,
                model=req.model,
                base_url=req.base_url,
                repo_path=req.metagpt_native_repo,
                rounds=req.metagpt_native_rounds,
                investment=req.metagpt_native_investment,
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
            if req.metagpt_native_only:
                result = {
                    "report": (
                        f"MetaGPT native completed.\n"
                        f"history={native.history_size}, cost={native.total_cost:.4f}, rounds={native.rounds}"
                    ),
                    "graph": "",
                }
                cache.set(cache_key, result, ttl_s=req.cache_ttl_s)
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
        "max_context_chars": req.max_context_chars or 32000,
        "max_context_tokens": req.max_context_tokens,
        "context_compress_type": req.context_compress_type or "summary_stub",
        "context_head_ratio": req.context_head_ratio if req.context_head_ratio is not None else 0.25,
        "context_matrix_rows": req.context_matrix_rows if req.context_matrix_rows is not None else 8,
        "context_matrix_cols": req.context_matrix_cols if req.context_matrix_cols is not None else 8,
        "context_sketch_dim": req.context_sketch_dim if req.context_sketch_dim is not None else 64,
        "tool_max_workers": req.tool_max_workers,
    }
    from app.core.task_split import split_task

    tasks = split_task(req.task, req.split_chunk_chars) if req.split_task else [req.task]
    reports: list[str] = []
    usage_totals = {"model_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    usage_lock = asyncio.Lock()
    split_max_concurrency = _resolve_split_max_concurrency(
        req.split_max_concurrency,
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
            stream_callback=stream_cb if req.stream else None,
            dialog_mode=req.dialog_mode,
            attention=req.attention,
            configurable=configurable,
        )
        chunk_usage = _extract_usage_metrics(state.messages)
        async with usage_lock:
            for k in usage_totals:
                usage_totals[k] += int(chunk_usage.get(k, 0))
            ExecutionStore.update(run_id, metrics=dict(usage_totals))
        payload = ChunkResult(index=idx, report=state.report, changes=state.change_log).model_dump()
        await bus.publish_event(run_id, {"type": "chunk_end", "payload": payload})
        return state.report or ""

    try:
        if req.split_task and len(tasks) > 1:
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
        ExecutionStore.update(run_id, status=STATUS_FINALIZING, stage="finalizing", progress="Finalizing results...")
        await bus.publish(run_id, events)
        result = {"report": "\n\n".join(reports), "graph": ""}
        cache.set(cache_key, result, ttl_s=req.cache_ttl_s)
        ExecutionStore.update(
            run_id,
            status=STATUS_FINISHED,
            stage="done",
            progress="Completed.",
            result=result,
            metrics={**native_metrics, **dict(usage_totals)},
        )
    except Exception as exc:
        ExecutionStore.update(
            run_id,
            status=STATUS_FAILED,
            stage="failed",
            progress=str(exc),
            result={"error": str(exc), "code": "E_AGENT_FAILED"},
        )
        await bus.publish_event(run_id, {"type": "run_error", "payload": {"error": str(exc), "code": "E_AGENT_FAILED"}})


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


async def _run_workflow_execution(
    run_id: str, req: WorkflowExecuteRequest, cache_key: str
) -> None:
    ExecutionStore.update(run_id, status=STATUS_RUNNING, stage="workflow", progress="Executing workflow...")
    model_max_concurrency = _resolve_model_max_concurrency(
        requested=req.model_max_concurrency,
        model=req.model,
        base_url=req.base_url,
    )
    model = create_chat_model(
        ModelConfig(
            api_key=req.api_key,
            model=req.model,
            base_url=req.base_url,
            max_concurrency=model_max_concurrency,
        ),
        provider=req.provider,
    )
    tools = {}
    workspace_root = Path(req.workspace)
    if req.enable_file_tools:
        tools.update(
            {
                "list_files": ListFilesTool(),
                "read_file": ReadFileTool(root=workspace_root),
                "write_file": WriteFileTool(root=workspace_root),
                "replace_in_file": ReplaceInFileTool(root=workspace_root),
                "apply_patch": ApplyPatchTool(root=workspace_root),
            }
        )
    if req.enable_command_tools:
        tools["run_tests"] = RunTestsTool(root=workspace_root)
    bus = get_event_bus()

    def emit(event: dict[str, Any]) -> None:
        asyncio.create_task(bus.publish_event(run_id, event))

    registry = create_default_registry()
    trace = TraceCollector(run_id=run_id, sink=emit)
    ctx = ExecutionContext(model=model, tools=tools, events=emit, trace=trace)
    executor = WorkflowExecutor(registry=registry, ctx=ctx)
    try:
        result = await executor.run(req.workflow, req.inputs)
        ExecutionStore.update(run_id, status=STATUS_FINALIZING, stage="finalizing", progress="Finalizing results...")
        payload = {"outputs": result.outputs, "node_outputs": result.node_outputs}
        cache.set(cache_key, payload, ttl_s=req.cache_ttl_s)
        ExecutionStore.update(run_id, status=STATUS_FINISHED, stage="done", progress="Completed.", result=payload)
    except Exception as exc:
        ExecutionStore.update(
            run_id,
            status=STATUS_FAILED,
            stage="failed",
            progress=str(exc),
            result={"error": str(exc), "code": "E_WORKFLOW_FAILED"},
        )
        await bus.publish_event(run_id, {"type": "run_error", "payload": {"error": str(exc), "code": "E_WORKFLOW_FAILED"}})


async def _run_generate(run_id: str, req: GenerateRequest, cache_key: str) -> None:
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
    try:
        model_max_concurrency = _resolve_model_max_concurrency(
            requested=req.model_max_concurrency,
            model=req.model,
            base_url=req.base_url,
        )
        model = create_chat_model(
            ModelConfig(
                api_key=req.api_key,
                model=req.model,
                base_url=req.base_url,
                max_concurrency=model_max_concurrency,
            ),
            provider=req.provider,
        )
        loop = asyncio.get_running_loop()

        def _token_cb(chunk) -> None:
            ExecutionStore.update(run_id, status=STATUS_STREAMING, stage="streaming", progress="Streaming model output...")
            asyncio.run_coroutine_threadsafe(
                bus.publish_event(run_id, {"type": "token", "payload": chunk.content}),
                loop,
            )

        model.stream_callback = _token_cb
        generator = OneShotGenerator(model=model, root=Path(req.workspace))
        cfg = GeneratorConfig(
            language=req.language,
            platforms=req.platforms,
            include_ci=req.include_ci,
            include_security=req.include_security,
            execute_workflow=req.execute_workflow,
            workflow_inputs=req.workflow_inputs,
            enable_file_tools=req.enable_file_tools,
            enable_command_tools=req.enable_command_tools,
            ai_codegen=req.ai_codegen,
            validate_commands=req.validate_commands,
            domain_targets=req.domain_targets,
            attention_scale=req.attention_scale,
            metagpt_chain=req.metagpt_chain,
            metagpt_native=req.metagpt_native,
            metagpt_native_repo=req.metagpt_native_repo,
            metagpt_native_rounds=req.metagpt_native_rounds,
            metagpt_native_investment=req.metagpt_native_investment,
            metagpt_native_only=req.metagpt_native_only,
            perspective=req.perspective,
            max_codegen_workers=req.max_codegen_workers,
            max_files=req.max_files,
            max_file_chunks=req.max_file_chunks,
            max_refine_rounds=req.max_refine_rounds,
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

        await asyncio.to_thread(generator.generate, req.requirement, cfg, _progress)
        ExecutionStore.update(run_id, status=STATUS_FINALIZING, stage="finalizing", progress="Finalizing generated project...")
        payload = {"workspace": req.workspace, "status": "generated"}
        cache.set(cache_key, payload, ttl_s=req.cache_ttl_s)
        ExecutionStore.update(run_id, status=STATUS_FINISHED, stage="done", progress="Completed.", result=payload)
        await bus.publish_event(run_id, {"type": "run_end", "payload": payload})
    except Exception as exc:
        ExecutionStore.update(
            run_id,
            status=STATUS_FAILED,
            stage="failed",
            progress=str(exc),
            result={"error": str(exc), "job_type": "generate", "code": "E_GENERATE_FAILED"},
        )
        await bus.publish_event(run_id, {"type": "run_error", "payload": {"error": str(exc), "code": "E_GENERATE_FAILED"}})
    finally:
        try:
            model.stream_callback = None  # type: ignore[name-defined]
        except Exception:
            pass
        stop_heartbeat = True
        heartbeat_task.cancel()
