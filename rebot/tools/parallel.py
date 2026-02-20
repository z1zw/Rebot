"""Parallel tool execution."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Iterable

from rebot.core.messages import Message, ToolCall
from rebot.tools.base import BaseTool


def execute_parallel(
    tools: dict[str, BaseTool], tool_calls: Iterable[ToolCall], max_workers: int | None = None
) -> list[Message]:
    results: list[Message] = []

    def run_one(call: ToolCall) -> Message:
        tool = tools.get(call.name)
        if tool is None:
            content = f"Unknown tool: {call.name}"
            meta = {"tool_call_id": call.id, "error": True}
        else:
            try:
                content = tool.run(call.args)
                meta = {"tool_call_id": call.id}
            except Exception as exc:  # noqa: BLE001
                content = f"Tool error: {exc}"
                meta = {"tool_call_id": call.id, "error": True}
        return Message(
            role="tool",
            content=content,
            name=call.name,
            metadata=meta,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for msg in executor.map(run_one, list(tool_calls)):
            results.append(msg)
    return results
