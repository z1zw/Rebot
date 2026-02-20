from __future__ import annotations

from app.api.models import SecurityTestRequest
from app.core.events import get_event_bus
from app.core.executions import ExecutionStore, STATUS_FINISHED, STATUS_RUNNING


async def run_security_test(run_id: str, req: SecurityTestRequest) -> None:
    from app.core.security_test import run_security_tests

    ExecutionStore.update(run_id, status=STATUS_RUNNING, stage="security", progress="Running security test...")
    bus = get_event_bus()
    await bus.publish_event(run_id, {"type": "security_test_start", "payload": {"target": req.target_url}})
    results = await run_security_tests(target_url=req.target_url, tools=req.tools)
    payload = [r.__dict__ for r in results]
    await bus.publish_event(run_id, {"type": "security_test_done", "payload": payload})
    ExecutionStore.update(run_id, status=STATUS_FINISHED, stage="done", progress="Completed.", result=payload)
