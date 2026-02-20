"""Agent state and middleware types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Literal, Protocol, TypeVar

from rebot.core.messages import Message

JumpTo = Literal["tools", "model", "end"]
StateT = TypeVar("StateT")
ContextT = TypeVar("ContextT")
ResponseT = TypeVar("ResponseT")


@dataclass
class AgentState(Generic[ResponseT]):
    messages: list[Message] = field(default_factory=list)
    jump_to: JumpTo | None = None
    structured_response: ResponseT | None = None
    change_log: list[str] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)
    report: str | None = None
    review_report: str | None = None
    execution_graph_mermaid: str | None = None
    execution_graph_png: str | None = None
    review_mode: bool = False
    callbacks: Any | None = None
    run_id: str | None = None
    span_id: str | None = None
    configurable: dict[str, Any] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    rc_stream_callback: Any | None = None
    reasoning_chain: str | None = None
    completion_hint: str | None = None
    reasoning_chain_structured: dict[str, Any] | None = None
    completion_structured: dict[str, Any] | None = None


class AgentMiddleware(Protocol[StateT, ContextT, ResponseT]):
    def before_agent(self, state: StateT, context: ContextT) -> dict[str, Any] | None:
        ...

    def before_model(self, state: StateT, context: ContextT) -> dict[str, Any] | None:
        ...

    def after_model(self, state: StateT, context: ContextT) -> dict[str, Any] | None:
        ...

    def after_agent(self, state: StateT, context: ContextT) -> dict[str, Any] | None:
        ...

    def wrap_model_call(
        self,
        messages: list[Message],
        tools: list[Any],
        kwargs: dict[str, Any],
        handler,
    ):
        ...

    async def awrap_model_call(
        self,
        messages: list[Message],
        tools: list[Any],
        kwargs: dict[str, Any],
        handler,
    ):
        ...

    def wrap_tool_call(self, tool_calls: list[Any], handler):
        ...
