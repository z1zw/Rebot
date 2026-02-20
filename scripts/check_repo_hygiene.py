from __future__ import annotations

import subprocess
import sys


FORBIDDEN_SEGMENTS = (
    "/node_modules/",
    "/.venv/",
    "/venv/",
    "/__pycache__/",
    "/.dart_tool/",
    "/.pub-cache/",
    "/.rebot/devserver/",
    "/.rebot/checkpoints/",
    "/.rebot/memory/",
)

FORBIDDEN_SUFFIXES = (
    ".pyc",
    ".pyo",
)


def _tracked_files() -> list[str]:
    cp = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    if cp.returncode != 0:
        print(cp.stderr.strip() or "git ls-files failed", file=sys.stderr)
        return []
    return [line.strip().replace("\\", "/") for line in cp.stdout.splitlines() if line.strip()]


def main() -> int:
    files = _tracked_files()
    if not files:
        return 0
    bad: list[str] = []
    for path in files:
        wrapped = f"/{path}"
        if path.startswith("workspace/") or path.startswith("backend/workspace/"):
            bad.append(path)
            continue
        if any(seg in wrapped for seg in FORBIDDEN_SEGMENTS):
            bad.append(path)
            continue
        if path.endswith(FORBIDDEN_SUFFIXES):
            bad.append(path)
            continue

    if not bad:
        print("repo_hygiene: ok")
        return 0

    print("repo_hygiene: forbidden tracked artifacts detected")
    for item in bad[:200]:
        print(f"- {item}")
    if len(bad) > 200:
        print(f"... and {len(bad) - 200} more")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
