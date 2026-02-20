"""Tool execution node."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from rebot.core.messages import Message, ToolCall
from rebot.tools.base import BaseTool


@dataclass
class ToolNode:
    tools: Sequence[BaseTool]
    max_workers: int | None = None

    @property
    def tools_by_name(self) -> dict[str, BaseTool]:
        return {t.name: t for t in self.tools}

    def execute(self, tool_calls: Iterable[ToolCall]) -> list[Message]:
        tools_by_name = self.tools_by_name
        from rebot.tools.parallel import execute_parallel

        return execute_parallel(tools_by_name, tool_calls, max_workers=self.max_workers)
