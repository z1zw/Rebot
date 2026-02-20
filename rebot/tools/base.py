"""Tool abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class BaseTool(Protocol):
    name: str
    description: str | None
    input_schema: dict[str, Any]
    return_direct: bool

    def run(self, args: dict[str, Any]) -> str:
        ...


@dataclass
class SimpleTool:
    name: str
    return_direct: bool
    handler: callable
    description: str | None = None
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.input_schema is None:
            self.input_schema = {"type": "object", "properties": {}}

    def run(self, args: dict[str, Any]) -> str:
        return self.handler(**args)
