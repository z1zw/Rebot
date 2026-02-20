from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import subprocess
import time

from app.core.process_sandbox import popen_checked, split_command
from app.core.startup_manager import StartupManager


@dataclass
class DevServerInfo:
    framework: str
    project_type: str
    workspace: str
    command: str
    port: int
    url: str
    started_at: float
    pid: int


class DevServerManager:
    _procs: dict[str, subprocess.Popen] = {}
    _info: dict[str, DevServerInfo] = {}

    @classmethod
    def _key(cls, workspace: str, framework: str) -> str:
        # Always use resolved absolute path for consistent key matching
        resolved = str(Path(workspace).resolve())
        return f"{resolved}::{framework}"

    @classmethod
    def _detect_pm(cls, workspace: Path) -> str:
        if (workspace / "pnpm-lock.yaml").exists():
            return "pnpm"
        if (workspace / "yarn.lock").exists():
            return "yarn"
        return "npm"

    @classmethod
    def log_tail(cls, *, workspace: str, framework: str, lines: int = 200) -> str:
        root = Path(workspace)
        log_file = root / ".rebot" / "devserver" / f"{framework}.log"
        if not log_file.exists():
            return ""
        try:
            content = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            n = max(1, min(int(lines), 1000))
            return "\n".join(content[-n:])
        except Exception:
            return ""

    @classmethod
    def start(
        cls,
        *,
        workspace: str,
        framework: str,
        project_type: str | None = None,
        port: int | None = None,
        command: str | None = None,
    ) -> DevServerInfo:
        root = Path(workspace)
        root.mkdir(parents=True, exist_ok=True)
        normalized_framework = StartupManager.normalize_framework(framework, project_type, root)
        normalized_project_type = StartupManager.normalize_project_type(project_type or normalized_framework)

        key = cls._key(workspace, normalized_framework)
        existing = cls._procs.get(key)
        if existing and existing.poll() is None:
            return cls._info[key]

        logs = root / ".rebot" / "devserver"
        logs.mkdir(parents=True, exist_ok=True)
        log_file = logs / f"{normalized_framework}.log"

        plan = StartupManager.build_plan(
            workspace=root,
            framework=normalized_framework,
            project_type=normalized_project_type,
            requested_port=port,
            command=command,
        )

        cmd = split_command(plan.command)
        if not cmd:
            raise ValueError("startup command is empty")
        proc = popen_checked(
            cmd,
            cwd=str(root),
            stdout=open(log_file, "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        info = DevServerInfo(
            framework=plan.framework,
            project_type=plan.project_type,
            workspace=workspace,
            command=plan.command,
            port=plan.port,
            url=f"http://localhost:{plan.port}",
            started_at=time.time(),
            pid=proc.pid,
        )
        cls._procs[key] = proc
        cls._info[key] = info
        return info

    @classmethod
    def stop(cls, *, workspace: str, framework: str) -> bool:
        key = cls._key(workspace, framework)
        proc = cls._procs.get(key)
        if proc is None:
            return False
        if proc.poll() is None:
            proc.terminate()
        cls._procs.pop(key, None)
        cls._info.pop(key, None)
        return True

    @classmethod
    def status(cls, *, workspace: str, framework: str) -> dict[str, Any]:
        key = cls._key(workspace, framework)
        proc = cls._procs.get(key)
        info = cls._info.get(key)
        if proc is None or info is None:
            return {"running": False}
        return {"running": proc.poll() is None, "info": info.__dict__}
