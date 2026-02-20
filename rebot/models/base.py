"""Model base and helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Protocol

from rebot.core.messages import Message, ToolCall
from rebot.tools.base import BaseTool


class ChatModel(Protocol):
    def invoke(self, messages: list[Message], *, tools: list[BaseTool], **kwargs: Any) -> Message:
        ...

    async def ainvoke(
        self, messages: list[Message], *, tools: list[BaseTool], **kwargs: Any
    ) -> Message:
        ...

    def stream(self, messages: list[Message], *, tools: list[BaseTool], **kwargs: Any):
        ...

    async def astream(self, messages: list[Message], *, tools: list[BaseTool], **kwargs: Any):
        ...


@dataclass
class ModelResponse:
    message: Message
    raw: dict[str, Any]


def _message_to_openai(msg: Message) -> dict[str, Any]:
    content = msg.content
    if not isinstance(content, str):
        if content is None:
            content = ""
        else:
            try:
                content = json.dumps(content, ensure_ascii=False)
            except Exception:
                content = str(content)
    payload: dict[str, Any] = {
        "role": msg.role,
        "content": content,
    }
    if msg.name and msg.role != "tool":
        payload["name"] = msg.name
    if msg.role == "tool":
        tool_call_id = msg.metadata.get("tool_call_id")
        if not tool_call_id:
            tool_call_id = msg.name or "tool_call"
        payload["tool_call_id"] = str(tool_call_id)
    if msg.tool_calls:
        def _tool_args_to_str(args: dict[str, Any]) -> str:
            try:
                return json.dumps(args or {}, ensure_ascii=False)
            except Exception:
                return str(args)

        payload["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": _tool_args_to_str(tc.args)},
            }
            for tc in msg.tool_calls
        ]
    return payload


def _tool_to_openai(tool: BaseTool) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


def _openai_to_message(payload: dict[str, Any]) -> Message:
    role = payload.get("role", "assistant")
    content = payload.get("content") or ""
    tool_calls = []
    for tc in payload.get("tool_calls", []) or []:
        fn = tc.get("function") or {}
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args_dict = json.loads(args) if args else {}
            except json.JSONDecodeError:
                args_dict = {"_raw": args}
        else:
            args_dict = args or {}
        tool_calls.append(ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), args=args_dict))
    return Message(role=role, content=content, tool_calls=tool_calls)
