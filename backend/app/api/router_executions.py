from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.events import get_event_bus
from app.core.executions import (
    ExecutionStore,
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_FINISHED,
)


router = APIRouter()


class ResumeExecutionRequest(BaseModel):
    api_key: str | None = None
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    workspace: str | None = None
    task: str | None = None
    multi_agent: bool | None = None
    role_model_overrides: dict | None = None
    max_token_budget: int | None = None
    max_cost_budget: float | None = None
    checkpoint_enabled: bool | None = None
    smoke_check_enabled: bool | None = None
    smoke_rework_budget: int | None = None
    priority: int | None = None
    resume_stage: str | None = None


@router.get("/executions")
async def list_executions(limit: int = 50):
    """List recent executions."""
    records = ExecutionStore.list_recent(limit=limit)
    return {
        "executions": [
            {
                "run_id": r.run_id,
                "status": r.status,
                "stage": r.stage,
                "progress": r.progress,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in records
        ],
        "count": len(records),
    }


@router.get("/executions/{run_id}")
async def get_execution(run_id: str):
    record = ExecutionStore.get(run_id)
    if record is None:
        return {"error": "not_found"}
    result = record.result
    if isinstance(result, dict) and "__runtime" in result:
        result = {k: v for k, v in result.items() if k != "__runtime"}
    return {
        "run_id": record.run_id,
        "status": record.status,
        "stage": record.stage,
        "progress": record.progress,
        "metrics": record.metrics,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "result": result,
    }


@router.post("/executions/{run_id}/cancel")
async def cancel_execution(run_id: str):
    record = ExecutionStore.get(run_id)
    if record is None:
        return {"ok": False, "error": "not_found"}
    if record.status in {STATUS_FINISHED, STATUS_FAILED, STATUS_CANCELLED}:
        return {"ok": True, "status": record.status}
    ExecutionStore.mark_cancelled(run_id, "Cancelled by user.")
    bus = get_event_bus()
    await bus.publish_event(
        run_id,
        {
            "type": "run_error",
            "payload": {"error": "Cancelled by user.", "code": "E_CANCELLED"},
        },
    )
    return {"ok": True, "status": STATUS_CANCELLED}


@router.get("/executions/{run_id}/checkpoint")
async def get_execution_checkpoint(run_id: str):
    record = ExecutionStore.get(run_id)
    if record is None:
        return {"ok": False, "error": "not_found"}
    checkpoint_path = str(record.metrics.get("checkpoint_path") or "").strip()
    if not checkpoint_path:
        return {"ok": False, "error": "checkpoint_path_missing"}
    p = Path(checkpoint_path)
    if not p.exists():
        return {"ok": False, "error": "checkpoint_not_found", "checkpoint_path": str(p)}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"checkpoint_parse_failed:{exc}", "checkpoint_path": str(p)}
    return {"ok": True, "checkpoint_path": str(p), "checkpoint": payload}


@router.post("/executions/{run_id}/resume")
async def resume_execution(run_id: str, req: ResumeExecutionRequest):
    record = ExecutionStore.get(run_id)
    if record is None:
        return {"ok": False, "error": "not_found"}
    source = record.metrics.get("request_payload")
    if not isinstance(source, dict):
        return {"ok": False, "error": "request_payload_missing"}

    payload = dict(source)
    if req.api_key is not None:
        payload["api_key"] = req.api_key
    if req.provider is not None:
        payload["provider"] = req.provider
    if req.model is not None:
        payload["model"] = req.model
    if req.base_url is not None:
        payload["base_url"] = req.base_url
    if req.workspace is not None:
        payload["workspace"] = req.workspace
    if req.task is not None:
        payload["task"] = req.task
    if req.multi_agent is not None:
        payload["multi_agent"] = req.multi_agent
    if req.role_model_overrides is not None:
        payload["role_model_overrides"] = req.role_model_overrides
    if req.max_token_budget is not None:
        payload["max_token_budget"] = req.max_token_budget
    if req.max_cost_budget is not None:
        payload["max_cost_budget"] = req.max_cost_budget
    if req.checkpoint_enabled is not None:
        payload["checkpoint_enabled"] = req.checkpoint_enabled
    if req.smoke_check_enabled is not None:
        payload["smoke_check_enabled"] = req.smoke_check_enabled
    if req.smoke_rework_budget is not None:
        payload["smoke_rework_budget"] = req.smoke_rework_budget
    if req.priority is not None:
        payload["priority"] = req.priority
    payload["resume_from_run_id"] = run_id
    if req.resume_stage is not None:
        payload["resume_checkpoint_stage"] = req.resume_stage

    payload["job_type"] = "agent"
    payload["cache_key"] = None

    from app.api.rest import RunRequest, run_autonomous

    run_req = RunRequest.model_validate(payload)
    resumed = await run_autonomous(run_req)
    return {"ok": True, "resumed_from": run_id, "run_id": resumed.run_id}
