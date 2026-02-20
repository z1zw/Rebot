from __future__ import annotations

import os
import sys
import tempfile
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODULE_PATH = ROOT / "rebot" / "tools" / "command_sandbox.py"
spec = importlib.util.spec_from_file_location("command_sandbox_local", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"failed to load module: {MODULE_PATH}")
command_sandbox = importlib.util.module_from_spec(spec)
sys.modules["command_sandbox_local"] = command_sandbox
spec.loader.exec_module(command_sandbox)
run_sandboxed = command_sandbox.run_sandboxed


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ok = run_sandboxed(command=f"\"{sys.executable}\" -c \"print('sandbox_ok')\"", root=root)
        _assert("exit=0" in ok and "sandbox_ok" in ok, f"allowed command failed: {ok}")

        try:
            run_sandboxed(command="git status", root=root)
            raise AssertionError("git status should be blocked by allowlist")
        except ValueError as exc:
            _assert("command not allowed" in str(exc), f"unexpected block reason: {exc}")

        shell_cmd = "cmd /c dir" if os.name == "nt" else "bash -lc ls"
        try:
            run_sandboxed(command=shell_cmd, root=root)
            raise AssertionError("shell executor should be denied")
        except ValueError as exc:
            _assert("executor denied" in str(exc), f"unexpected shell block reason: {exc}")

        prev_timeout = os.getenv("REBOT_CMD_TIMEOUT_S")
        os.environ["REBOT_CMD_TIMEOUT_S"] = "1"
        try:
            timed = run_sandboxed(
                command=f"\"{sys.executable}\" -c \"import time; time.sleep(2); print('late')\"",
                root=root,
            )
            _assert("exit=124" in timed, f"timeout not enforced: {timed}")
        finally:
            if prev_timeout is None:
                os.environ.pop("REBOT_CMD_TIMEOUT_S", None)
            else:
                os.environ["REBOT_CMD_TIMEOUT_S"] = prev_timeout


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"[FAIL] command sandbox smoke failed: {exc}")
        sys.exit(1)
    print("[OK] command sandbox smoke passed")
