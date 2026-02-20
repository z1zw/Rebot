from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import time
import uuid
import json

from app.core.db import upsert_execution, get_execution

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_STREAMING = "streaming"
STATUS_FINALIZING = "finalizing"
STATUS_FINISHED = "finished"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

ACTIVE_STATUSES = {STATUS_QUEUED, STATUS_RUNNING, STATUS_STREAMING, STATUS_FINALIZING}


@dataclass
class ExecutionRecord:
    run_id: str
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    result: dict[str, Any] | None = None
    cache_key: str | None = None
    stage: str | None = None
    progress: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class ExecutionStore:
    _records: dict[str, ExecutionRecord] = {}

    @classmethod
    def create(cls) -> ExecutionRecord:
        run_id = uuid.uuid4().hex
        record = ExecutionRecord(run_id=run_id, status=STATUS_QUEUED, stage=STATUS_QUEUED, progress="Task queued.")
        cls._records[run_id] = record
        upsert_execution(run_id, record.status, record.created_at, record.updated_at, None)
        return record

    @classmethod
    def find_active_by_request_key(cls, request_key: str) -> ExecutionRecord | None:
        if not request_key:
            return None
        now = time.time()
        for run_id in list(cls._records.keys()):
            rec = cls.get(run_id)
            if rec is None:
                continue
            if rec.status not in ACTIVE_STATUSES:
                continue
            if rec.metrics.get("request_key") == request_key:
                # Avoid reviving stale queue entries forever.
                if now - rec.updated_at > 3600:
                    continue
                return rec
        return None

    @classmethod
    def mark_cancelled(cls, run_id: str, reason: str = "Cancelled by user.") -> None:
        cls.update(
            run_id,
            status=STATUS_CANCELLED,
            stage=STATUS_CANCELLED,
            progress=reason,
            result={"error": reason, "code": "E_CANCELLED"},
        )

    @classmethod
    def get(cls, run_id: str) -> ExecutionRecord | None:
        db_record = get_execution(run_id)
        cached = cls._records.get(run_id)
        if db_record is None:
            return cached
        loaded = ExecutionRecord(
            run_id=db_record.run_id,
            status=db_record.status,
            created_at=db_record.created_at,
            updated_at=db_record.updated_at,
            result=json.loads(db_record.result) if db_record.result else None,
        )
        cls._hydrate_runtime(loaded)
        if cached is None or loaded.updated_at >= cached.updated_at:
            cls._records[run_id] = loaded
            return loaded
        return cached

    @classmethod
    def update(
        cls,
        run_id: str,
        *,
        status: str | None = None,
        result: dict[str, Any] | None = None,
        stage: str | None = None,
        progress: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        record = cls._records.get(run_id)
        if record is None:
            db_record = get_execution(run_id)
            if db_record is None:
                now = time.time()
                record = ExecutionRecord(
                    run_id=run_id,
                    status="pending",
                    created_at=now,
                    updated_at=now,
                    result=None,
                )
            else:
                record = ExecutionRecord(
                    run_id=db_record.run_id,
                    status=db_record.status,
                    created_at=db_record.created_at,
                    updated_at=db_record.updated_at,
                    result=json.loads(db_record.result) if db_record.result else None,
                )
                cls._hydrate_runtime(record)
            cls._records[run_id] = record
        if status is not None:
            record.status = status
        if result is not None:
            record.result = result
        if stage is not None:
            record.stage = stage
        if progress is not None:
            record.progress = progress
        if metrics:
            record.metrics.update(metrics)
        record.updated_at = time.time()
        persisted = cls._with_runtime(record)
        upsert_execution(
            record.run_id,
            record.status,
            record.created_at,
            record.updated_at,
            json.dumps(persisted) if persisted is not None else None,
        )

    @staticmethod
    def _with_runtime(record: ExecutionRecord) -> dict[str, Any] | None:
        if record.result is None and not record.stage and not record.progress and not record.metrics:
            return None
        data: dict[str, Any] = dict(record.result or {})
        data["__runtime"] = {
            "stage": record.stage,
            "progress": record.progress,
            "metrics": record.metrics,
        }
        return data

    @staticmethod
    def _hydrate_runtime(record: ExecutionRecord) -> None:
        if not isinstance(record.result, dict):
            return
        runtime = record.result.get("__runtime")
        if not isinstance(runtime, dict):
            return
        record.stage = runtime.get("stage")
        record.progress = runtime.get("progress")
        metrics = runtime.get("metrics")
        if isinstance(metrics, dict):
            record.metrics = metrics

    @classmethod
    def list_recent(cls, limit: int = 50) -> list[ExecutionRecord]:
        """List recent executions sorted by updated_at descending."""
        # Combine in-memory and cached records
        all_records: dict[str, ExecutionRecord] = {}
        for run_id, record in cls._records.items():
            all_records[run_id] = record
        # Sort by updated_at descending
        sorted_records = sorted(
            all_records.values(),
            key=lambda r: r.updated_at,
            reverse=True
        )
        return sorted_records[:limit]
