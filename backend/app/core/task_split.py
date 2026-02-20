from __future__ import annotations

from typing import Iterable


def split_task(task: str, max_chunk_chars: int = 800) -> list[str]:
    if len(task) <= max_chunk_chars:
        return [task]
    chunks: list[str] = []
    start = 0
    while start < len(task):
        end = min(start + max_chunk_chars, len(task))
        chunks.append(task[start:end].strip())
        start = end
    return [c for c in chunks if c]
