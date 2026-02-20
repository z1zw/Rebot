"""Structured output tool wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class StructuredOutputTool:
    name: str
    description: str | None
    input_schema: dict[str, Any]
    return_direct: bool = True

    def run(self, args: dict[str, Any]) -> str:
        return "structured output tool should not be executed directly"
