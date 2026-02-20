from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from rebot.tools.fs_tools import normalize_tool_path


def safe_join_workspace(workspace_root: Path, rel_path: str) -> Path:
    root = workspace_root.resolve()
    target, _ = normalize_and_validate_path(root, rel_path)
    return target


def normalize_and_validate_path(root: Path, raw_path: str) -> tuple[Path, str]:
    root = root.resolve()
    clean = normalize_tool_path(root, raw_path)
    target = (root / clean).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Path escapes workspace: {raw_path}")
    return target, clean


def file_depth(path: Path, root: Path) -> int:
    try:
        return len(path.resolve().relative_to(root.resolve()).parts)
    except Exception:
        return 999


def scan_workspace_files(root: Path, max_depth: int = 8) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(seg in {".git", ".rebot", "node_modules", ".venv", "__pycache__"} for seg in p.parts):
            continue
        if file_depth(p, root) > max_depth:
            continue
        files.append(p)
    return files


def pick_misaligned_subdir(root: Path, files: list[Path]) -> Path | None:
    if not files:
        return None
    entry_names = {"index.html", "package.json", "pubspec.yaml", "main.dart", "vite.config.ts", "next.config.js"}
    scored: dict[Path, int] = {}
    for f in files:
        if f.parent == root:
            continue
        score = 1
        if f.name in entry_names:
            score += 5
        scored[f.parent] = scored.get(f.parent, 0) + score
    if not scored:
        return None
    ranked = sorted(scored.items(), key=lambda x: (-x[1], file_depth(x[0], root)))
    best_dir, _ = ranked[0]
    if file_depth(best_dir, root) <= 0:
        return None
    return best_dir


def repair_workspace_layout(root: Path, max_depth: int = 8) -> dict[str, Any]:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    files = scan_workspace_files(root, max_depth=max_depth)
    immediate_files = [f for f in files if f.parent == root]
    immediate_entry = {
        f.name.lower()
        for f in immediate_files
        if f.name.lower()
        in {"index.html", "package.json", "pubspec.yaml", "main.dart", "next.config.js", "pages.json", "manifest.json"}
    }
    moved: list[str] = []
    skipped: list[str] = []

    if immediate_entry:
        return {
            "workspace": str(root),
            "moved": moved,
            "skipped": skipped,
            "source": None,
            "already_aligned": True,
        }

    source = pick_misaligned_subdir(root, files)
    if source is None:
        return {
            "workspace": str(root),
            "moved": moved,
            "skipped": skipped,
            "source": None,
            "already_aligned": False,
        }

    for item in source.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(source)
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            skipped.append(str(rel).replace("\\", "/"))
            continue
        shutil.move(str(item), str(target))
        moved.append(str(rel).replace("\\", "/"))
    return {
        "workspace": str(root),
        "moved": moved,
        "skipped": skipped,
        "source": str(source),
        "already_aligned": False,
    }


def detect_entrypoint(root: Path, framework: str) -> Path | None:
    import logging

    fw = (framework or "").strip().lower()
    candidates: list[Path]
    if fw == "flutter":
        candidates = [root / "pubspec.yaml", root / "lib" / "main.dart"]
    elif fw in {"react", "nextjs", "uniapp", "vue"}:
        candidates = [root / "package.json", root / "index.html", root / "frontend" / "index.html"]
    elif fw == "html":
        candidates = [root / "index.html", root / "frontend" / "index.html"]
    elif fw in {"python", "general"}:
        candidates = [root, root / "index.html", root / "frontend" / "index.html", root / "main.py", root / "app.py"]
    elif fw == "wechat_miniprogram":
        candidates = [root / "project.config.json", root / "app.json"]
    else:
        candidates = [root / "index.html", root / "package.json", root / "pubspec.yaml"]
    logging.info(f"[detect_entrypoint] fw={fw} root={root} candidates={[str(c) for c in candidates]}")
    for c in candidates:
        exists = c.exists()
        logging.info(f"[detect_entrypoint] checking {c} exists={exists}")
        if exists:
            return c
    return None


def candidate_entry_names(framework: str) -> set[str]:
    fw = (framework or "").strip().lower()
    if fw == "flutter":
        return {"pubspec.yaml", "main.dart"}
    if fw == "nextjs":
        return {"package.json", "next.config.js", "index.html"}
    if fw == "uniapp":
        return {"package.json", "pages.json", "manifest.json", "index.html"}
    if fw in {"react", "html", "vue"}:
        return {"index.html", "package.json"}
    if fw in {"python", "general"}:
        return {"index.html", "main.py", "app.py", "package.json"}
    if fw == "wechat_miniprogram":
        return {"project.config.json", "app.json"}
    return {"index.html", "package.json", "pubspec.yaml"}


def ensure_entrypoint_alignment(root: Path, framework: str, max_depth: int = 8) -> dict[str, Any]:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    existing = detect_entrypoint(root, framework)
    if existing is not None:
        return {"ok": True, "moved": [], "source": None, "entry": str(existing)}

    names = candidate_entry_names(framework)
    candidates: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.name not in names:
            continue
        if any(seg in {".git", ".rebot", "node_modules", ".venv", "__pycache__"} for seg in p.parts):
            continue
        if file_depth(p, root) > max_depth:
            continue
        candidates.append(p)

    if not candidates:
        return {"ok": False, "moved": [], "source": None, "entry": None}

    candidates.sort(key=lambda p: (file_depth(p, root), len(str(p))))
    source = candidates[0].parent
    if source == root:
        return {"ok": False, "moved": [], "source": None, "entry": None}

    moved: list[str] = []
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(source)
        if ".rebot" in str(rel):
            continue
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            continue
        try:
            shutil.move(str(item), str(target))
            moved.append(str(rel).replace("\\", "/"))
        except PermissionError:
            pass

    entry = detect_entrypoint(root, framework)
    return {
        "ok": entry is not None,
        "moved": moved,
        "source": str(source),
        "entry": str(entry) if entry is not None else None,
    }
