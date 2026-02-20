"""Dynamic tool registration middleware."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rebot.agents.middleware import AgentState


@dataclass
class DynamicToolMiddleware:
    tools: list[Any] = field(default_factory=list)

    def wrap_model_call(self, messages, tools, kwargs, handler):
        merged = list(tools) + list(self.tools)
        return handler(messages, merged, kwargs)

    def wrap_tool_call(self, tool_calls, handler):
        return handler(tool_calls)
