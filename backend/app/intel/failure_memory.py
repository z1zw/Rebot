from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class FailureMemory:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "failure_playbook.jsonl"
        self.rows: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            lines = self.path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            return
        buf: list[dict[str, Any]] = []
        for line in lines[-4000:]:
            raw = line.strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except Exception:
                continue
            if isinstance(parsed, dict):
                buf.append(parsed)
        self.rows = buf

    @staticmethod
    def _keywords(text: str) -> list[str]:
        words = re.findall(r"[a-zA-Z0-9_./:-]+", (text or "").lower())
        stop = {
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "from",
            "task",
            "project",
            "file",
            "files",
            "build",
            "create",
            "production",
            "quality",
            "failed",
            "failure",
            "error",
        }
        out: list[str] = []
        for w in words:
            if len(w) < 3 or w in stop:
                continue
            out.append(w)
            if len(out) >= 120:
                break
        return out

    @staticmethod
    def _normalize_issue(issue: str) -> str:
        s = (issue or "").strip().lower()
        s = re.sub(r"[0-9]+", "#", s)
        s = re.sub(r"\s+", " ", s)
        return s[:220]

    def add_case(
        self,
        *,
        query: str,
        framework: str,
        issues: list[str] | None,
        success: bool,
        resolution: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        sigs = [self._normalize_issue(x) for x in (issues or []) if str(x).strip()]
        sigs = [x for x in sigs if x]
        row = {
            "query": (query or "")[:1200],
            "framework": (framework or "").strip().lower() or "unknown",
            "success": bool(success),
            "issue_signatures": sigs[:16],
            "resolution": (resolution or "")[:2400],
            "metadata": metadata or {},
            "keywords": self._keywords(
                "\n".join(
                    [
                        query or "",
                        framework or "",
                        "\n".join(sigs[:16]),
                        resolution or "",
                    ]
                )
            ),
        }
        self.rows.append(row)
        if len(self.rows) > 4000:
            self.rows = self.rows[-4000:]
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def query(self, *, query: str, framework: str, top_k: int = 3) -> list[str]:
        if not self.rows:
            return []
        qk = set(self._keywords(query))
        fw = (framework or "").strip().lower()
        scored: list[tuple[float, dict[str, Any]]] = []
        for row in self.rows[-2500:]:
            try:
                kws = set(str(x).lower() for x in (row.get("keywords") or []) if str(x).strip())
                if not kws:
                    continue
                overlap = len(qk & kws)
                if overlap <= 0:
                    continue
                score = overlap / max(1, len(qk))
                row_fw = str(row.get("framework") or "").strip().lower()
                if fw and row_fw and fw == row_fw:
                    score += 0.35
                if row.get("success") is True:
                    score += 0.08
                scored.append((score, row))
            except Exception:
                continue
        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[str] = []
        seen: set[str] = set()
        for _, row in scored:
            sigs = [str(x).strip() for x in (row.get("issue_signatures") or []) if str(x).strip()]
            res = str(row.get("resolution") or "").strip()
            row_fw = str(row.get("framework") or "").strip().lower()
            if row.get("success") is True:
                text = (
                    f"failure_playbook_success[{row_fw or 'unknown'}]: "
                    f"reuse repair path; key fixes={'; '.join(sigs[:3]) or 'none'}; "
                    f"resolution={res[:300] or 'n/a'}"
                )
            else:
                text = (
                    f"failure_playbook_risk[{row_fw or 'unknown'}]: "
                    f"avoid repeated blockers={'; '.join(sigs[:4]) or 'unknown'}; "
                    f"add targeted repair before finishing"
                )
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(text)
            if len(out) >= max(1, top_k):
                break
        return out
