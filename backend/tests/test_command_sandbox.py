from __future__ import annotations

import os
import sys
from pathlib import Path

from rebot.tools.command_sandbox import SandboxPolicy, run_sandboxed


def test_run_sandboxed_allows_python(tmp_path: Path):
    out = run_sandboxed(command=f"\"{sys.executable}\" -c \"print('ok')\"", root=tmp_path)
    assert "exit=0" in out
    assert "ok" in out


def test_run_sandboxed_blocks_unknown_command(tmp_path: Path):
    try:
        run_sandboxed(command="git status", root=tmp_path)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "command not allowed" in str(exc)


def test_run_sandboxed_blocks_shell_executor(tmp_path: Path):
    shell_cmd = "cmd /c dir" if os.name == "nt" else "bash -lc ls"
    try:
        run_sandboxed(command=shell_cmd, root=tmp_path)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "executor denied" in str(exc)


def test_run_sandboxed_timeout(tmp_path: Path):
    policy = SandboxPolicy(allowed_commands={"python", "py"}, timeout_s=1, max_output_chars=20000)
    out = run_sandboxed(
        command=f"\"{sys.executable}\" -c \"import time; time.sleep(2); print('late')\"",
        root=tmp_path,
        policy=policy,
    )
    assert "exit=124" in out
