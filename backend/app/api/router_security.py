from __future__ import annotations

import asyncio

from fastapi import APIRouter

from app.api.models import ExecuteResponse, SecurityTestRequest
from app.api.services.security_service import run_security_test
from app.core.executions import ExecutionStore


router = APIRouter()


@router.post("/security/test", response_model=ExecuteResponse)
async def security_test(req: SecurityTestRequest):
    record = ExecutionStore.create()
    asyncio.create_task(run_security_test(record.run_id, req))
    return ExecuteResponse(run_id=record.run_id)
