from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
import hashlib
import re

from rebot.agents.vector_memory import VectorMemory


class ExperienceMemory:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._mode = "local_hybrid"
        self._local = VectorMemory(path=self.base_dir / "experience_memory.json")
        self._local.load()
        self._tips_path = self.base_dir / "experience_tips.jsonl"
        self._tips: list[dict[str, Any]] = []
        self._load_tips()
        self._chroma = None
        self._collection = None
        self._chroma_enabled = os.getenv("REBOT_EXPERIENCE_CHROMA_ENABLED", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if self._chroma_enabled:
            self._init_chroma()

    def _init_chroma(self) -> None:
        try:
            import chromadb  # type: ignore

            self._chroma = chromadb.PersistentClient(path=str(self.base_dir / "chroma"))
            self._collection = self._chroma.get_or_create_collection("rebot_experience")
            self._mode = "chroma"
        except Exception:
            self._mode = "local_hybrid"

    def _load_tips(self) -> None:
        if not self._tips_path.exists():
            return
        try:
            lines = self._tips_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            buf: list[dict[str, Any]] = []
            for line in lines[-2000:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        buf.append(row)
                except Exception:
                    continue
            self._tips = buf
        except Exception:
            self._tips = []

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        words = re.findall(r"[a-zA-Z0-9_./-]+", (text or "").lower())
        stop = {
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "from",
            "into",
            "your",
            "task",
            "project",
            "file",
            "files",
            "build",
            "create",
        }
        out: list[str] = []
        for w in words:
            if len(w) < 3 or w in stop:
                continue
            out.append(w)
        return out[:80]

    def _append_tip(self, *, query: str, resolution: str, metadata: dict[str, Any]) -> None:
        row = {
            "query": query,
            "resolution": resolution[:8000],
            "metadata": metadata,
            "keywords": self._extract_keywords(f"{query}\n{resolution}"),
        }
        self._tips.append(row)
        if len(self._tips) > 3000:
            self._tips = self._tips[-3000:]
        try:
            self._tips_path.parent.mkdir(parents=True, exist_ok=True)
            with self._tips_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def add(self, query: str, resolution: str, metadata: dict[str, Any] | None = None) -> None:
        text = f"query: {query}\nresolution: {resolution}".strip()
        meta = metadata or {}
        self._append_tip(query=query, resolution=resolution, metadata=meta)
        if self._mode == "chroma" and self._collection is not None:
            doc_id = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
            try:
                self._collection.upsert(
                    documents=[text],
                    metadatas=[meta],
                    ids=[doc_id],
                )
                return
            except Exception:
                self._mode = "local_hybrid"
        self._local.add(text, metadata=meta)
        self._local.save()

    def _query_tips(self, query: str, top_k: int) -> list[str]:
        qk = set(self._extract_keywords(query))
        if not qk or not self._tips:
            return []
        scored: list[tuple[float, str]] = []
        for row in self._tips[-1200:]:
            try:
                kws = set(str(x).lower() for x in (row.get("keywords") or []) if str(x).strip())
                if not kws:
                    continue
                inter = len(qk & kws)
                if inter <= 0:
                    continue
                # Prefer concrete remediation from resolution text.
                res = str(row.get("resolution") or "").strip()
                if not res:
                    continue
                score = inter / max(len(qk), 1)
                scored.append((score, f"memory_tip: {res[:1800]}"))
            except Exception:
                continue
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[: max(1, top_k)]]

    def query(self, query: str, top_k: int = 4) -> list[str]:
        out: list[str] = []
        out.extend(self._query_tips(query=query, top_k=top_k))
        if self._mode == "chroma" and self._collection is not None:
            try:
                res = self._collection.query(query_texts=[query], n_results=max(1, top_k))
                docs = res.get("documents") or []
                if docs and isinstance(docs[0], list):
                    out.extend([str(x) for x in docs[0] if str(x).strip()])
            except Exception:
                self._mode = "local_hybrid"
        hits = self._local.search(query, top_k=max(1, top_k))
        out.extend([str(item.get("text", "")) for item in hits if str(item.get("text", "")).strip()])
        dedup: list[str] = []
        seen: set[str] = set()
        for x in out:
            key = x.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            dedup.append(key)
            if len(dedup) >= max(1, top_k):
                break
        return dedup

    @property
    def mode(self) -> str:
        return self._mode
