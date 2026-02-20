"""Filesystem tools for coding tasks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple
import os


def _canonical_path(root: Path, raw: str) -> Tuple[Path, str]:
    root = root.resolve()
    value = str(raw or "").strip()
    if not value:
        raise ValueError("path is empty")

    value = value.replace("\\", "/").strip()
    if value.startswith("file://"):
        value = value[7:]

    value = value.lstrip("/").strip()
    if not value:
        raise ValueError("path is empty")

    relative_candidate = Path(value)
    if relative_candidate.is_absolute():
        target = relative_candidate.resolve(strict=False)
    else:
        candidate = root / relative_candidate
        target = candidate.resolve(strict=False)

    canonical_root = str(root)
    canonical_target = str(target)
    common = os.path.commonpath([canonical_root, canonical_target])
    if common != canonical_root:
        raise ValueError("path escapes workspace root")

    try:
        rel_path = os.path.relpath(canonical_target, canonical_root)
    except ValueError as exc:
        raise ValueError("path escapes workspace root") from exc

    if not rel_path or rel_path == ".":
        raise ValueError("path is empty")

    canonical = os.path.normpath(rel_path).replace("\\", "/")
    blocked_dirs = {".rebot", ".git", "node_modules", ".venv", "__pycache__"}
    for part in Path(canonical).parts:
        if part in blocked_dirs:
            raise ValueError(f"path '{raw}' targets restricted directory '{part}'")
    return Path(canonical_target), canonical


def normalize_tool_path(root: Path, raw: str) -> str:
    _, canonical = _canonical_path(root, raw)
    return canonical


def _resolve_path(root: Path, raw: str) -> Path:
    target, _ = _canonical_path(root, raw)
    return target


@dataclass
class ListFilesTool:
    name: str = "list_files"
    description: str | None = "List files under a root directory."
    input_schema: dict[str, Any] = None
    return_direct: bool = False

    def __post_init__(self) -> None:
        if self.input_schema is None:
            self.input_schema = {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_depth": {"type": "integer", "minimum": 0},
                },
                "required": ["path"],
            }

    def run(self, args: dict[str, Any]) -> str:
        root = Path(args["path"]).resolve()
        max_depth = int(args.get("max_depth", 3))
        if max_depth < 0:
            max_depth = 0
        items: list[str] = []
        for p in root.rglob("*"):
            rel = p.relative_to(root)
            if len(rel.parts) > max_depth:
                continue
            items.append(str(rel))
        return "\n".join(sorted(items))


@dataclass
class ReadFileTool:
    name: str = "read_file"
    description: str | None = "Read a text file."
    input_schema: dict[str, Any] = None
    return_direct: bool = False
    root: Path | None = None

    def __post_init__(self) -> None:
        if self.input_schema is None:
            self.input_schema = {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            }

    def run(self, args: dict[str, Any]) -> str:
        if self.root is None:
            raise ValueError("root not set")
        path = _resolve_path(self.root, args["path"])
        if not path.exists():
            raise ValueError(f"path not found: {args['path']}")
        if path.is_dir():
            raise ValueError(f"path is a directory: {args['path']}")
        try:
            return path.read_text(encoding="utf-8")
        except PermissionError as exc:
            raise ValueError(f"permission denied: {args['path']}") from exc


@dataclass
class WriteFileTool:
    name: str = "write_file"
    description: str | None = "Write a text file, overwriting if exists."
    input_schema: dict[str, Any] = None
    return_direct: bool = False
    root: Path | None = None

    def __post_init__(self) -> None:
        if self.input_schema is None:
            self.input_schema = {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            }

    def run(self, args: dict[str, Any]) -> str:
        if self.root is None:
            raise ValueError("root not set")
        path = _resolve_path(self.root, args["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"], encoding="utf-8")
        return f"Wrote {path}"


@dataclass
class ReplaceInFileTool:
    name: str = "replace_in_file"
    description: str | None = "Replace text in a file."
    input_schema: dict[str, Any] = None
    return_direct: bool = False
    root: Path | None = None

    def __post_init__(self) -> None:
        if self.input_schema is None:
            self.input_schema = {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                    "count": {"type": "integer", "minimum": 1},
                },
                "required": ["path", "old", "new"],
            }

    def run(self, args: dict[str, Any]) -> str:
        if self.root is None:
            raise ValueError("root not set")
        path = _resolve_path(self.root, args["path"])
        count = int(args.get("count", 1))
        content = path.read_text(encoding="utf-8")
        if args["old"] not in content:
            return "No matches found."
        updated = content.replace(args["old"], args["new"], count)
        path.write_text(updated, encoding="utf-8")
        return f"Replaced {count} occurrence(s) in {path}"


@dataclass
class ApplyPatchTool:
    name: str = "apply_patch"
    description: str | None = "Apply a unified diff patch."
    input_schema: dict[str, Any] = None
    return_direct: bool = False
    root: Path | None = None

    def __post_init__(self) -> None:
        if self.input_schema is None:
            self.input_schema = {
                "type": "object",
                "properties": {"patch": {"type": "string"}},
                "required": ["patch"],
            }

    def run(self, args: dict[str, Any]) -> str:
        if self.root is None:
            raise ValueError("root not set")
        patch = args["patch"]
        try:
            from rebot.tools.patch_apply import apply_patch

            apply_patch(self.root, patch)
            return "Patch applied."
        except Exception as exc:  # noqa: BLE001
            return f"Patch failed: {exc}"
