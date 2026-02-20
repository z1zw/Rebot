"""Block registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from rebot.workflows.blocks.base import Block


Factory = Callable[[dict[str, Any]], Block]


@dataclass
class BlockRegistry:
    factories: dict[str, Factory] = field(default_factory=dict)

    def register(self, type_name: str, factory: Factory) -> None:
        self.factories[type_name] = factory

    def create(self, type_name: str, config: dict[str, Any]) -> Block:
        if type_name not in self.factories:
            raise RuntimeError(f"Unknown block type: {type_name}")
        return self.factories[type_name](config)
