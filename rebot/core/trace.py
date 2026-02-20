"""Unified trace collector for runnable/agent/workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
import time


@dataclass
class TraceCollector:
    run_id: str
    sink: Callable[[dict[str, Any]], None] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, event_type: str, name: str, payload: dict[str, Any], span_id: str = "") -> None:
        event = {
            "type": event_type,
            "name": name,
            "payload": payload,
            "run_id": self.run_id,
            "span_id": span_id,
            "ts": time.time(),
        }
        self.events.append(event)
        if self.sink:
            self.sink(event)

    def on_start(self, name: str, payload: dict[str, Any]) -> None:
        self.emit("runnable_start", name, payload)

    def on_end(self, name: str, payload: dict[str, Any]) -> None:
        self.emit("runnable_end", name, payload)

    def on_error(self, name: str, payload: dict[str, Any]) -> None:
        self.emit("runnable_error", name, payload)

    def on_run_start(self, name: str, inputs: dict[str, Any], run_id: str) -> None:
        self.emit("run_start", name, inputs)

    def on_run_end(self, name: str, outputs: dict[str, Any], run_id: str) -> None:
        self.emit("run_end", name, outputs)

    def on_model_start(self, name: str, inputs: dict[str, Any], run_id: str, span_id: str) -> None:
        self.emit("model_start", name, inputs, span_id=span_id)

    def on_model_end(self, name: str, outputs: dict[str, Any], run_id: str, span_id: str) -> None:
        self.emit("model_end", name, outputs, span_id=span_id)

    def on_tool_start(self, name: str, inputs: dict[str, Any], run_id: str, span_id: str) -> None:
        self.emit("tool_start", name, inputs, span_id=span_id)

    def on_tool_end(self, name: str, outputs: dict[str, Any], run_id: str, span_id: str) -> None:
        self.emit("tool_end", name, outputs, span_id=span_id)
