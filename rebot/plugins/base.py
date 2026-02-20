"""Plugin interfaces."""

from __future__ import annotations

from typing import Protocol


class Plugin(Protocol):
    name: str

    def init(self) -> None:
        ...

    def shutdown(self) -> None:
        ...
