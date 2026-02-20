"""Lightweight serialization helpers."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from rebot.core.messages import Message, ToolCall
from rebot.agents.middleware import AgentState
from rebot.core.runnable import RunnableConfig


def to_dict(obj: Any) -> dict[str, Any]:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, Message):
        return {
            "role": obj.role,
            "content": obj.content,
            "name": obj.name,
            "tool_calls": [to_dict(tc) for tc in obj.tool_calls],
            "metadata": obj.metadata,
        }
    if isinstance(obj, ToolCall):
        return {"id": obj.id, "name": obj.name, "args": obj.args}
    if isinstance(obj, AgentState):
        return {
            "messages": [to_dict(m) for m in obj.messages],
            "jump_to": obj.jump_to,
            "structured_response": obj.structured_response,
            "change_log": obj.change_log,
            "plan": obj.plan,
            "report": obj.report,
            "review_report": obj.review_report,
            "execution_graph_mermaid": obj.execution_graph_mermaid,
            "execution_graph_png": obj.execution_graph_png,
            "review_mode": obj.review_mode,
            "run_id": obj.run_id,
            "span_id": obj.span_id,
            "configurable": obj.configurable,
            "events": obj.events,
        }
    if isinstance(obj, RunnableConfig):
        return {
            "tags": obj.tags,
            "metadata": obj.metadata,
            "max_concurrency": obj.max_concurrency,
            "configurable": obj.configurable,
            "configurable_schema": obj.configurable_schema,
            "run_id": obj.run_id,
        }
    raise TypeError(f"Unsupported type for serialization: {type(obj)}")
