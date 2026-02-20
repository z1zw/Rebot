"""Command execution tool (opt-in)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rebot.tools.command_sandbox import run_sandboxed


@dataclass
class RunTestsTool:
    name: str = "run_tests"
    description: str | None = "Run project tests and return output."
    input_schema: dict[str, Any] = None
    return_direct: bool = False
    root: Path | None = None

    def __post_init__(self) -> None:
        if self.input_schema is None:
            self.input_schema = {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            }

    def run(self, args: dict[str, Any]) -> str:
        if self.root is None:
            raise ValueError("root not set")
        cmd = str(args["command"])
        return run_sandboxed(command=cmd, root=self.root)
