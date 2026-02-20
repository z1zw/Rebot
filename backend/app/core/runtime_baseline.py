from __future__ import annotations

import shutil
import subprocess
from typing import Any


_TOOL_COMMANDS: dict[str, tuple[str, ...]] = {
    "python": ("python", "python3", "python.exe"),
    "node": ("node", "node.exe"),
    "npm": ("npm", "npm.cmd"),
    "flutter": ("flutter", "flutter.bat"),
    "dart": ("dart", "dart.exe"),
}

_TOOL_MISSING_MESSAGES: dict[str, str] = {
    "python": "Missing Python environment, please install Python.",
    "node": "Missing Node.js environment, please install it.",
    "npm": "Missing npm environment, please install Node.js/npm.",
    "flutter": "Missing Flutter environment, please install Flutter SDK.",
    "dart": "Missing Dart environment, please install Flutter SDK (includes Dart).",
}

_FRAMEWORK_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "general": ("python",),
    "html": ("python",),
    "python": ("python",),
    "react": ("node", "npm"),
    "vue": ("node", "npm"),
    "nextjs": ("node", "npm"),
    "uniapp": ("node", "npm"),
    "flutter": ("flutter", "dart"),
}


def _normalize_framework(framework: str | None) -> str:
    fw = (framework or "").strip().lower()
    if fw in {"", "general"}:
        return "general"
    if fw == "miniprogram":
        return "wechat_miniprogram"
    return fw


def _resolve_tool_command(tool: str) -> str | None:
    for candidate in _TOOL_COMMANDS.get(tool, ()):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def _read_version(command_path: str | None) -> str:
    if not command_path:
        return ""
    try:
        cp = subprocess.run(
            [command_path, "--version"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        out = (cp.stdout or cp.stderr or "").strip()
        if not out:
            return ""
        return out.splitlines()[0][:160]
    except Exception:
        return ""


def collect_runtime_baseline(*, include_versions: bool = True) -> dict[str, Any]:
    tools: dict[str, dict[str, Any]] = {}
    for tool in _TOOL_COMMANDS:
        command_path = _resolve_tool_command(tool)
        available = bool(command_path)
        tools[tool] = {
            "available": available,
            "command_path": command_path or "",
            "version": _read_version(command_path) if include_versions and available else "",
        }

    frameworks: dict[str, dict[str, Any]] = {}
    for framework, required in _FRAMEWORK_REQUIREMENTS.items():
        missing = [name for name in required if not tools.get(name, {}).get("available")]
        frameworks[framework] = {
            "ready": len(missing) == 0,
            "required_tools": list(required),
            "missing_tools": missing,
            "missing_messages": [_TOOL_MISSING_MESSAGES[x] for x in missing],
        }

    core_tools = ("python", "node", "npm", "flutter", "dart")
    core_missing = [name for name in core_tools if not tools.get(name, {}).get("available")]
    return {
        "tools": tools,
        "frameworks": frameworks,
        "summary": {
            "core_ready": len(core_missing) == 0,
            "core_missing": core_missing,
        },
    }


def preflight_for_framework(framework: str | None) -> tuple[bool, list[str]]:
    fw = _normalize_framework(framework)
    if fw == "wechat_miniprogram":
        return False, [
            "WeChat MiniProgram preview requires WeChat DevTools. Configure devtools path and project root."
        ]
    baseline = collect_runtime_baseline(include_versions=False)
    frameworks = baseline.get("frameworks")
    if not isinstance(frameworks, dict):
        return True, []
    target = frameworks.get(fw)
    if not isinstance(target, dict):
        target = frameworks.get("general")
    if not isinstance(target, dict):
        return True, []
    ready = bool(target.get("ready"))
    missing_messages = target.get("missing_messages")
    if isinstance(missing_messages, list):
        return ready, [str(x) for x in missing_messages if str(x).strip()]
    return ready, []
