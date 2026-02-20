from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import os
import shlex
import subprocess


DEFAULT_ALLOWED_COMMANDS = {
    "cargo",
    "dart",
    "dotnet",
    "flutter",
    "go",
    "gradle",
    "gradlew",
    "jest",
    "mvn",
    "npm",
    "npx",
    "pnpm",
    "py",
    "pytest",
    "python",
    "python3",
    "uv",
    "vitest",
    "yarn",
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


@dataclass(frozen=True)
class SandboxPolicy:
    allowed_commands: set[str]
    timeout_s: int
    max_output_chars: int

    @classmethod
    def from_env(cls) -> SandboxPolicy:
        allowed_raw = os.getenv("REBOT_CMD_ALLOWED", "").strip()
        if allowed_raw:
            allowed = {x.strip().lower() for x in allowed_raw.split(",") if x.strip()}
        else:
            allowed = set(DEFAULT_ALLOWED_COMMANDS)
        timeout_s = _parse_int(os.getenv("REBOT_CMD_TIMEOUT_S", "120"), default=120, min_value=1, max_value=3600)
        max_output_chars = _parse_int(
            os.getenv("REBOT_CMD_MAX_OUTPUT_CHARS", "20000"),
            default=20000,
            min_value=1000,
            max_value=200000,
        )
        return cls(allowed_commands=allowed, timeout_s=timeout_s, max_output_chars=max_output_chars)


def _parse_int(raw: str, *, default: int, min_value: int, max_value: int) -> int:
    try:
        n = int(raw)
    except Exception:
        return default
    return max(min_value, min(max_value, n))


def _resolve_cwd(root: Path) -> Path:
    cwd = root.resolve()
    if not cwd.exists():
        raise ValueError(f"workspace does not exist: {cwd}")
    if not cwd.is_dir():
        raise ValueError(f"workspace is not a directory: {cwd}")
    return cwd


def _executable_name(token: str) -> str:
    name = Path(token.strip().strip('"').strip("'")).name.lower()
    for suffix in (".exe", ".cmd", ".bat"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def split_command(command: str) -> list[str]:
    cmd = str(command or "").strip()
    if not cmd:
        raise ValueError("empty command")
    tokens = [_strip_wrapping_quotes(t) for t in shlex.split(cmd, posix=False)]
    if not tokens:
        raise ValueError("empty command")
    return tokens


def _strip_wrapping_quotes(token: str) -> str:
    t = token.strip()
    if len(t) >= 2 and ((t[0] == '"' and t[-1] == '"') or (t[0] == "'" and t[-1] == "'")):
        return t[1:-1]
    return t


def assert_command_allowed(tokens: Iterable[str], policy: SandboxPolicy) -> None:
    arr = list(tokens)
    if not arr:
        raise ValueError("empty command")
    exe = _executable_name(arr[0])
    if exe in DENIED_EXECUTORS:
        raise ValueError(f"command executor denied: {exe}")
    if exe not in policy.allowed_commands:
        allow = ", ".join(sorted(policy.allowed_commands))
        raise ValueError(f"command not allowed: {exe}. allowed: {allow}")


def _cap_output(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n...[truncated {len(text) - max_chars} chars]"


def run_sandboxed(*, command: str, root: Path, policy: SandboxPolicy | None = None) -> str:
    p = policy or SandboxPolicy.from_env()
    tokens = split_command(command)
    assert_command_allowed(tokens, p)
    cwd = _resolve_cwd(root)
    try:
        completed = subprocess.run(  # noqa: S603, S607
            tokens,
            cwd=str(cwd),
            shell=False,
            capture_output=True,
            text=True,
            timeout=p.timeout_s,
        )
        out = (completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or "")
        out = _cap_output(out, p.max_output_chars)
        return f"exit={completed.returncode}\n{out}"
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") + ("\n" if exc.stdout and exc.stderr else "") + (exc.stderr or "")
        out = _cap_output(out, p.max_output_chars)
        return f"exit=124\ntimeout={p.timeout_s}s\n{out}"
