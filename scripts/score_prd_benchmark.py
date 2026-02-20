#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SOURCE_EXTS = {
    ".py",
    ".dart",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".json",
    ".md",
    ".yml",
    ".yaml",
}

PLACEHOLDER_PATTERNS = (
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bTBD\b",
    r"placeholder",
    r"coming soon",
    r"mock data",
)


@dataclass
class CaseSpec:
    case_id: str
    prompt: str
    framework: str
    expected_files: list[str]
    expected_keywords: list[str]


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _load_cases(path: Path) -> dict[str, CaseSpec]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = {}
    for item in raw.get("cases", []):
        cid = str(item.get("id", "")).strip()
        if not cid:
            continue
        cases[cid] = CaseSpec(
            case_id=cid,
            prompt=str(item.get("prompt", "")),
            framework=str(item.get("framework", "")).lower().strip(),
            expected_files=[str(x).replace("\\", "/") for x in item.get("expected_files", [])],
            expected_keywords=[str(x).lower().strip() for x in item.get("expected_keywords", [])],
        )
    return cases


def _collect_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file()]


def _framework_entry_ok(framework: str, rel_paths: set[str]) -> tuple[float, list[str]]:
    required_by_framework = {
        "flutter": {"pubspec.yaml", "lib/main.dart"},
        "react": {"package.json", "index.html"},
        "vue": {"package.json", "index.html"},
        "nextjs": {"package.json"},
        "python": {"main.py"},
        "html": {"index.html"},
    }
    required = required_by_framework.get(framework, set())
    if not required:
        return 100.0, []
    hit = [p for p in required if p in rel_paths]
    score = (len(hit) / max(len(required), 1)) * 100.0
    missing = [p for p in required if p not in rel_paths]
    return score, missing


def _score_case(case: CaseSpec, workspace: Path) -> dict[str, Any]:
    files = _collect_files(workspace)
    rel_paths = {str(p.relative_to(workspace)).replace("\\", "/") for p in files}
    source_files = [p for p in files if p.suffix.lower() in SOURCE_EXTS]

    file_hits = [f for f in case.expected_files if f in rel_paths]
    file_cov = (len(file_hits) / max(len(case.expected_files), 1)) * 100.0

    corpus = "\n".join(_read_text_safe(p).lower() for p in source_files[:600])
    kw_hits = [k for k in case.expected_keywords if k and k in corpus]
    interaction_cov = (len(kw_hits) / max(len(case.expected_keywords), 1)) * 100.0

    responsive_signals = ("mediaquery", "layoutbuilder", "@media", "responsive", "breakpoint", "mobile")
    design_signals = ("theme", "token", "color", "typography", "spacing", "radius")
    responsive_score = 100.0 if any(s in corpus for s in responsive_signals) else 45.0
    design_score = 100.0 if any(s in corpus for s in design_signals) else 55.0
    ux_score = 0.6 * responsive_score + 0.4 * design_score

    entry_score, missing_entries = _framework_entry_ok(case.framework, rel_paths)

    placeholder_hits = 0
    for patt in PLACEHOLDER_PATTERNS:
        placeholder_hits += len(re.findall(patt, corpus, flags=re.IGNORECASE))
    hygiene_score = max(0.0, 100.0 - min(placeholder_hits * 7.0, 70.0))

    total = (
        file_cov * 0.30
        + entry_score * 0.20
        + interaction_cov * 0.20
        + ux_score * 0.15
        + hygiene_score * 0.15
    )
    verdict = "pass" if total >= 80 else ("warn" if total >= 65 else "fail")

    return {
        "case_id": case.case_id,
        "prompt": case.prompt,
        "framework": case.framework,
        "workspace": str(workspace),
        "scores": {
            "file_coverage": round(file_cov, 2),
            "runtime_entry": round(entry_score, 2),
            "interaction": round(interaction_cov, 2),
            "ux_design": round(ux_score, 2),
            "hygiene": round(hygiene_score, 2),
            "total": round(total, 2),
        },
        "evidence": {
            "expected_files_hit": file_hits,
            "missing_entries": missing_entries,
            "expected_keywords_hit": kw_hits,
            "placeholder_hits": placeholder_hits,
            "source_file_count": len(source_files),
        },
        "verdict": verdict,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score generated projects with PRD benchmark rubric.")
    parser.add_argument("--benchmark", default="scripts/prd_benchmark_cases.json", help="Benchmark JSON path.")
    parser.add_argument("--case-id", help="Single benchmark case id.")
    parser.add_argument("--workspace", help="Workspace path for single-case scoring.")
    parser.add_argument(
        "--manifest",
        help="JSON file mapping case_id -> workspace path for batch scoring.",
    )
    parser.add_argument("--output", help="Optional report output JSON path.")
    args = parser.parse_args()

    cases = _load_cases(Path(args.benchmark))
    results: list[dict[str, Any]] = []

    if args.manifest:
        mapping = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        for cid, ws in mapping.items():
            cid = str(cid).strip()
            if cid not in cases:
                continue
            root = Path(str(ws)).expanduser().resolve()
            if not root.exists():
                continue
            results.append(_score_case(cases[cid], root))
    else:
        if not args.case_id or not args.workspace:
            raise SystemExit("Single mode requires --case-id and --workspace.")
        if args.case_id not in cases:
            raise SystemExit(f"Unknown case id: {args.case_id}")
        root = Path(args.workspace).expanduser().resolve()
        if not root.exists():
            raise SystemExit(f"Workspace not found: {root}")
        results.append(_score_case(cases[args.case_id], root))

    summary_total = round(sum(r["scores"]["total"] for r in results) / max(len(results), 1), 2)
    report = {
        "benchmark": str(Path(args.benchmark).resolve()),
        "cases_evaluated": len(results),
        "average_total_score": summary_total,
        "results": results,
    }

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
