from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence
import os
import shlex
import subprocess


DEFAULT_ALLOWED_COMMANDS = {
    "adb",
    "emulator",
    "flutter",
    "git",
    "node",
    "npm",
    "npx",
    "nuclei",
    "pnpm",
    "py",
    "python",
    "python3",
    "scrcpy",
    "yarn",
    "zap-baseline.py",
}

DENIED_EXECUTORS = {
    "bash",
    "cmd",
    "cmd.exe",
    "fish",
    "powershell",
    "powershell.exe",
    "pwsh",
    "sh",
    "zsh",
}


def _parse_allowlist() -> set[str]:
    raw = os.getenv("REBOT_PROC_ALLOWED", "").strip()
    if not raw:
        return set(DEFAULT_ALLOWED_COMMANDS)
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def _normalize_exe(token: str) -> str:
    name = Path(str(token or "").strip().strip('"').strip("'")).name.lower()
    for suffix in (".exe", ".cmd", ".bat"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def split_command(command: str) -> list[str]:
    cmd = str(command or "").strip()
    if not cmd:
        raise ValueError("empty command")
    parts = [x.strip().strip('"').strip("'") for x in shlex.split(cmd, posix=False)]
    parts = [x for x in parts if x]
    if not parts:
        raise ValueError("empty command")
    return parts


def assert_allowed(tokens: Sequence[str], *, allowed: set[str] | None = None) -> None:
    if not tokens:
        raise ValueError("empty command")
    allow = allowed or _parse_allowlist()
    exe = _normalize_exe(tokens[0])
    if exe in DENIED_EXECUTORS:
        raise ValueError(f"executor denied: {exe}")
    if exe not in allow:
        raise ValueError(f"command not allowed: {exe}")


def _resolve_cwd(cwd: Path | str | None) -> str | None:
    if cwd is None:
        return None
    p = Path(cwd).resolve()
    if not p.exists() or not p.is_dir():
        raise ValueError(f"invalid cwd: {p}")
    return str(p)


def run_checked(
    cmd: Sequence[str] | str,
    *,
    cwd: Path | str | None = None,
    timeout: int | float | None = None,
    capture_output: bool = True,
    text: bool = True,
    allowed: set[str] | None = None,
) -> subprocess.CompletedProcess:
    tokens = split_command(cmd) if isinstance(cmd, str) else [str(x) for x in cmd]
    assert_allowed(tokens, allowed=allowed)
    return subprocess.run(  # noqa: S603, S607
        tokens,
        cwd=_resolve_cwd(cwd),
        shell=False,
        timeout=timeout,
        capture_output=capture_output,
        text=text,
        check=False,
    )


def popen_checked(
    cmd: Sequence[str] | str,
    *,
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
    stdout=None,
    stderr=None,
    creationflags: int = 0,
    allowed: set[str] | None = None,
) -> subprocess.Popen:
    tokens = split_command(cmd) if isinstance(cmd, str) else [str(x) for x in cmd]
    assert_allowed(tokens, allowed=allowed)
    return subprocess.Popen(  # noqa: S603
        tokens,
        cwd=_resolve_cwd(cwd),
        shell=False,
        env=env,
        stdout=stdout,
        stderr=stderr,
        creationflags=creationflags,
    )


def is_allowed_command(command: str, *, allowed: set[str] | None = None) -> bool:
    try:
        tokens = split_command(command)
        assert_allowed(tokens, allowed=allowed)
        return True
    except Exception:
        return False
