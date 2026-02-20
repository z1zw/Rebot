"""Lightweight vector memory with hashing embeddings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import math
import re


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def _hash_vector(text: str, dim: int = 256) -> list[float]:
    vec = [0.0] * dim
    for tok in _tokens(text):
        idx = hash(tok) % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@dataclass
class VectorMemory:
    path: Path
    dim: int = 256
    items: list[dict[str, Any]] = field(default_factory=list)

    def load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.items = list(data.get("items", []))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"dim": self.dim, "items": self.items}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        vec = _hash_vector(text, self.dim)
        self.items.append(
            {
                "text": text,
                "vector": vec,
                "metadata": metadata or {},
            }
        )

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        q = _hash_vector(query, self.dim)
        scored = []
        for item in self.items:
            score = _cosine(q, item.get("vector", []))
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for score, item in scored[:top_k]]
