"""Workflow block base types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from rebot.models.base import ChatModel
from rebot.tools.base import BaseTool


@dataclass
class ExecutionContext:
    model: ChatModel | None = None
    tools: dict[str, BaseTool] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    events: callable | None = None
    trace: Any | None = None

    def emit(self, event: dict[str, Any]) -> None:
        if self.events:
            self.events(event)


class Block(Protocol):
    async def run(self, ctx: ExecutionContext, inputs: dict[str, Any]) -> dict[str, Any]:
        ...
