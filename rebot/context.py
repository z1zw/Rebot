"""Global context and cost management."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CostManager:
    total_tokens: int = 0
    total_cost: float = 0.0

    def record(self, tokens: int, cost: float) -> None:
        self.total_tokens += tokens
        self.total_cost += cost


@dataclass
class Context:
    config: dict[str, Any] = field(default_factory=dict)
    cost_manager: CostManager = field(default_factory=CostManager)
    llm: Any | None = None
    replay: list[dict[str, Any]] = field(default_factory=list)
