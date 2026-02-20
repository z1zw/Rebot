"""Memory interfaces."""

from __future__ import annotations

from typing import Any, Protocol


class MemoryStore(Protocol):
    def put(self, key: str, value: Any) -> None:
        ...

    def get(self, key: str) -> Any | None:
        ...
