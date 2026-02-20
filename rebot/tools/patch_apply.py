"""Patch application utilities."""

from __future__ import annotations

from pathlib import Path


def apply_patch(root: Path, patch_text: str) -> None:
    lines = patch_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- "):
            old_path = line[4:].strip()
            i += 1
            if i >= len(lines) or not lines[i].startswith("+++ "):
                raise ValueError("invalid patch: missing +++")
            new_path = lines[i][4:].strip()
            i += 1
            target_path = _pick_path(old_path, new_path)
            file_path = (root / target_path).resolve()
            if root not in file_path.parents and file_path != root:
                raise ValueError("patch path escapes workspace root")
            file_lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
            while i < len(lines) and lines[i].startswith("@@"):
                i, file_lines = _apply_hunk(i, lines, file_lines)
            file_path.write_text("".join(file_lines), encoding="utf-8")
        else:
            i += 1


def _pick_path(old_path: str, new_path: str) -> str:
    if new_path != "/dev/null":
        return _strip_prefix(new_path)
    return _strip_prefix(old_path)


def _strip_prefix(path: str) -> str:
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _apply_hunk(idx: int, lines: list[str], file_lines: list[str]) -> tuple[int, list[str]]:
    header = lines[idx]
    if not header.startswith("@@"):
        raise ValueError("invalid hunk header")
    idx += 1
    out: list[str] = []
    src = 0
    if file_lines:
        out.extend(file_lines)
    cursor = 0
    while idx < len(lines):
        line = lines[idx]
        if line.startswith("@@") or line.startswith("--- "):
            break
        if line.startswith(" "):
            cursor += 1
        elif line.startswith("-"):
            if cursor < len(out):
                out.pop(cursor)
        elif line.startswith("+"):
            out.insert(cursor, line[1:] + "\n")
            cursor += 1
        idx += 1
    return idx, out
