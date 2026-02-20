from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
import json
import socket

from app.core.process_sandbox import is_allowed_command
from app.core.runtime_baseline import preflight_for_framework


@dataclass
class StartupPlan:
    framework: str
    project_type: str
    port: int
    command: str
    notes: list[str]


class StartupManager:
    @classmethod
    def normalize_project_type(cls, value: str | None) -> str:
        v = (value or "").strip().lower()
        if v in {"wechat", "wechat_miniprogram", "mini_program", "miniprogram"}:
            return "wechat_miniprogram"
        if v in {"uni", "uni-app", "uniapp"}:
            return "uniapp"
        if v in {"general", "native", "generic"}:
            return "general"
        if v in {"react", "nextjs", "flutter", "python", "html", "vue"}:
            return v
        return "general"

    @classmethod
    def normalize_framework(cls, framework: str | None, project_type: str | None, workspace: Path) -> str:
        fw = (framework or "").strip().lower()
        pt = cls.normalize_project_type(project_type)
        if fw in {"wechat", "wechat_miniprogram", "mini_program", "miniprogram"}:
            return "wechat_miniprogram"
        if fw in {"uni", "uni-app", "uniapp"}:
            return "uniapp"
        if fw in {"html", "react", "nextjs", "flutter", "python", "general", "vue"}:
            return fw
        if pt != "general":
            return pt
        return cls._infer_framework_from_workspace(workspace)

    @classmethod
    def preflight(cls, framework: str) -> tuple[bool, list[str]]:
        return preflight_for_framework(framework)

    @classmethod
    def build_plan(
        cls,
        *,
        workspace: Path,
        framework: str | None,
        project_type: str | None,
        requested_port: int | None,
        command: str | None,
    ) -> StartupPlan:
        fw = cls.normalize_framework(framework, project_type, workspace)
        pt = cls.normalize_project_type(project_type or fw)
        port = requested_port or cls._suggest_port(workspace, fw)
        if command and command.strip():
            custom = command.strip()
            if not is_allowed_command(custom):
                raise ValueError("custom startup command is not allowed by process sandbox policy")
            return StartupPlan(framework=fw, project_type=pt, port=port, command=custom, notes=[])
        cmd = cls._build_command(workspace, fw, port)
        return StartupPlan(framework=fw, project_type=pt, port=port, command=cmd, notes=[])

    @classmethod
    def _infer_framework_from_workspace(cls, workspace: Path) -> str:
        root = workspace.resolve()
        if (root / "pubspec.yaml").exists():
            return "flutter"
        if (root / "pages.json").exists() or (root / "manifest.json").exists():
            return "uniapp"
        if (root / "next.config.js").exists():
            return "nextjs"
        if (root / "package.json").exists():
            return "react"
        if (root / "index.html").exists() or (root / "frontend" / "index.html").exists():
            return "html"
        return "general"

    @classmethod
    def _detect_pm(cls, workspace: Path) -> str:
        if (workspace / "pnpm-lock.yaml").exists():
            return "pnpm"
        if (workspace / "yarn.lock").exists():
            return "yarn"
        return "npm"

    @classmethod
    def _read_scripts(cls, workspace: Path) -> dict[str, Any]:
        pkg = workspace / "package.json"
        if not pkg.exists():
            return {}
        try:
            raw = json.loads(pkg.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("scripts"), dict):
                return raw.get("scripts") or {}
        except Exception:
            return {}
        return {}

    @classmethod
    def _has_script(cls, scripts: dict[str, Any], name: str) -> bool:
        v = scripts.get(name)
        return isinstance(v, str) and v.strip() != ""

    @classmethod
    def _build_command(cls, workspace: Path, framework: str, port: int) -> str:
        workspace = workspace.resolve()
        pm = cls._detect_pm(workspace)
        scripts = cls._read_scripts(workspace)
        frontend_index = workspace / "frontend" / "index.html"
        root_index = workspace / "index.html"
        static_root = workspace / "frontend" if frontend_index.exists() else workspace

        if framework == "flutter":
            return f"flutter run -d web-server --web-port {port} --web-hostname 0.0.0.0"
        if framework == "nextjs":
            if cls._has_script(scripts, "dev"):
                return f"{pm} run dev -- -H 0.0.0.0 -p {port}"
            return f'python -m http.server {port} --bind 0.0.0.0 --directory "{static_root}"'
        if framework in {"react", "vue"}:
            if cls._has_script(scripts, "dev"):
                return f"{pm} run dev -- --host 0.0.0.0 --port {port}"
            if cls._has_script(scripts, "start"):
                return f"{pm} run start -- --host 0.0.0.0 --port {port}"
            return f'python -m http.server {port} --bind 0.0.0.0 --directory "{static_root}"'
        if framework == "uniapp":
            if cls._has_script(scripts, "dev:h5"):
                return f"{pm} run dev:h5 -- --host 0.0.0.0 --port {port}"
            if cls._has_script(scripts, "dev"):
                return f"{pm} run dev -- --host 0.0.0.0 --port {port}"
            return f'python -m http.server {port} --bind 0.0.0.0 --directory "{static_root}"'
        if framework in {"python", "general", "html"}:
            return f'python -m http.server {port} --bind 0.0.0.0 --directory "{static_root if (frontend_index.exists() or root_index.exists()) else workspace}"'
        if cls._has_script(scripts, "dev"):
            return f"{pm} run dev -- --host 0.0.0.0 --port {port}"
        return f'python -m http.server {port} --bind 0.0.0.0 --directory "{workspace}"'

    @classmethod
    def _base_port(cls, framework: str) -> int:
        mapping = {
            "flutter": 5200,
            "nextjs": 3000,
            "react": 5173,
            "vue": 5174,
            "uniapp": 5175,
            "html": 8080,
            "python": 8081,
            "general": 8082,
            "wechat_miniprogram": 9418,
        }
        return mapping.get(framework, 5173)

    @classmethod
    def _suggest_port(cls, workspace: Path, framework: str) -> int:
        base = cls._base_port(framework)
        seed = int(hashlib.sha1(str(workspace.resolve()).encode("utf-8")).hexdigest()[:8], 16)
        start = base + (seed % 200)
        for p in range(start, start + 60):
            if cls._is_port_free(p):
                return p
        return start

    @classmethod
    def _is_port_free(cls, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", int(port)))
                return True
            except OSError:
                return False
