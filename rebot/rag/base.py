"""RAG interfaces."""

from __future__ import annotations

from typing import Protocol


class Retriever(Protocol):
    def retrieve(self, query: str) -> list[str]:
        ...
