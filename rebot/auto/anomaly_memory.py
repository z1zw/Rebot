"""Anomaly memory and adaptive attention."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AnomalyMemory:
    path: Path
    counts: dict[str, int] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    clusters: dict[str, list[str]] = field(default_factory=dict)

    def load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.counts = dict(data.get("counts", {}))
        self.weights = dict(data.get("weights", {}))
        self.clusters = dict(data.get("clusters", {}))

    def save(self) -> None:
        payload = {"counts": self.counts, "weights": self.weights, "clusters": self.clusters}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def update(self, anomalies: list[dict[str, Any]]) -> None:
        for item in anomalies:
            name = str(item.get("name") or "unknown")
            severity = float(item.get("severity", 0.2))
            self.counts[name] = self.counts.get(name, 0) + 1
            current = self.weights.get(name, 0.0)
            boosted = min(1.0, current + 0.1 + severity * 0.2)
            self.weights[name] = boosted
            cluster = self._cluster_key(name)
            bucket = self.clusters.get(cluster, [])
            if name not in bucket:
                bucket.append(name)
            self.clusters[cluster] = bucket

    def decay(self, rate: float = 0.92, floor: float = 0.05) -> None:
        for key, weight in list(self.weights.items()):
            self.weights[key] = max(floor, weight * rate)

    def summary(self) -> dict[str, Any]:
        return {
            "counts": self.counts,
            "weights": self.weights,
            "clusters": self.clusters,
        }

    def attention_boost(self) -> dict[str, float]:
        return dict(self.weights)

    def frequency_boost(self, cap: float = 0.6) -> dict[str, float]:
        boost: dict[str, float] = {}
        for name, count in self.counts.items():
            boost[name] = min(cap, 0.05 * count)
        return boost

    def _cluster_key(self, name: str) -> str:
        if name.startswith("missing_"):
            return "missing_files"
        if "validation" in name or "test" in name:
            return "validation"
        if "frontend" in name:
            return "frontend"
        if "backend" in name:
            return "backend"
        if "ios" in name or "mobile" in name:
            return "mobile"
        return "general"
