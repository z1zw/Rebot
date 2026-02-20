"""Callback and tracing utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol
import time


class CallbackHandler(Protocol):
    def on_run_start(self, name: str, inputs: dict[str, Any], run_id: str) -> None:
        ...

    def on_run_end(self, name: str, outputs: dict[str, Any], run_id: str) -> None:
        ...

    def on_model_start(
        self, name: str, inputs: dict[str, Any], run_id: str, span_id: str
    ) -> None:
        ...

    def on_model_end(
        self, name: str, outputs: dict[str, Any], run_id: str, span_id: str
    ) -> None:
        ...

    def on_tool_start(
        self, name: str, inputs: dict[str, Any], run_id: str, span_id: str
    ) -> None:
        ...

    def on_tool_end(
        self, name: str, outputs: dict[str, Any], run_id: str, span_id: str
    ) -> None:
        ...


@dataclass
class CallbackManager:
    handlers: list[CallbackHandler] = field(default_factory=list)

    def on_run_start(self, name: str, inputs: dict[str, Any], run_id: str) -> None:
        for h in self.handlers:
            h.on_run_start(name, inputs, run_id)

    def on_run_end(self, name: str, outputs: dict[str, Any], run_id: str) -> None:
        for h in self.handlers:
            h.on_run_end(name, outputs, run_id)

    def on_model_start(
        self, name: str, inputs: dict[str, Any], run_id: str, span_id: str
    ) -> None:
        for h in self.handlers:
            h.on_model_start(name, inputs, run_id, span_id)

    def on_model_end(
        self, name: str, outputs: dict[str, Any], run_id: str, span_id: str
    ) -> None:
        for h in self.handlers:
            h.on_model_end(name, outputs, run_id, span_id)

    def on_tool_start(
        self, name: str, inputs: dict[str, Any], run_id: str, span_id: str
    ) -> None:
        for h in self.handlers:
            h.on_tool_start(name, inputs, run_id, span_id)

    def on_tool_end(
        self, name: str, outputs: dict[str, Any], run_id: str, span_id: str
    ) -> None:
        for h in self.handlers:
            h.on_tool_end(name, outputs, run_id, span_id)


@dataclass
class EventStreamHandler:
    events: list[dict[str, Any]] = field(default_factory=list)

    def _push(self, event_type: str, name: str, payload: dict[str, Any], run_id: str, span_id: str) -> None:
        self.events.append(
            {
                "type": event_type,
                "name": name,
                "payload": payload,
                "run_id": run_id,
                "span_id": span_id,
                "ts": time.time(),
            }
        )

    def on_run_start(self, name: str, inputs: dict[str, Any], run_id: str) -> None:
        self._push("run_start", name, inputs, run_id, span_id="")

    def on_run_end(self, name: str, outputs: dict[str, Any], run_id: str) -> None:
        self._push("run_end", name, outputs, run_id, span_id="")

    def on_model_start(
        self, name: str, inputs: dict[str, Any], run_id: str, span_id: str
    ) -> None:
        self._push("model_start", name, inputs, run_id, span_id)

    def on_model_end(
        self, name: str, outputs: dict[str, Any], run_id: str, span_id: str
    ) -> None:
        self._push("model_end", name, outputs, run_id, span_id)

    def on_tool_start(
        self, name: str, inputs: dict[str, Any], run_id: str, span_id: str
    ) -> None:
        self._push("tool_start", name, inputs, run_id, span_id)

    def on_tool_end(
        self, name: str, outputs: dict[str, Any], run_id: str, span_id: str
    ) -> None:
        self._push("tool_end", name, outputs, run_id, span_id)


def create_event_manager(events: list[dict[str, Any]]) -> CallbackManager:
    return CallbackManager(handlers=[EventStreamHandler(events=events)])
