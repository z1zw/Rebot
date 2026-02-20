from __future__ import annotations

from pydantic import BaseModel
from typing import Any


class ChunkResult(BaseModel):
    index: int
    report: str | None = None
    changes: list[str] = []
    errors: list[str] = []


class EventEnvelope(BaseModel):
    type: str
    payload: dict[str, Any]
