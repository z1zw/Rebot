from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.models import (
    DevServerLogsRequest,
    DevServerRestartRequest,
    DevServerResponse,
    DevServerStartRequest,
    DevServerStatusRequest,
    DevServerStopRequest,
)
from app.api.services.preview_service import await_preview_health
from app.api.services.workspace_service import (
    detect_entrypoint,
    ensure_entrypoint_alignment,
    repair_workspace_layout,
)
from app.core.devserver import DevServerManager
from app.core.runtime_baseline import collect_runtime_baseline
from app.core.startup_manager import StartupManager


router = APIRouter()


def _static_fallback_command(root: Path, port: int) -> str:
    static_root = root / "frontend" if (root / "frontend" / "index.html").exists() else root
    return f'python -m http.server {int(port)} --bind 0.0.0.0 --directory "{static_root.resolve()}"'


async def _health_with_config(url: str) -> dict:
    return await await_preview_health(
        url,
        retries=max(6, int(os.getenv("REBOT_PREVIEW_HEALTH_RETRIES", "12"))),
        delay=max(0.2, float(os.getenv("REBOT_PREVIEW_HEALTH_DELAY_S", "0.5"))),
    )


@router.get("/devserver/runtime-baseline")
async def runtime_baseline():
    return collect_runtime_baseline(include_versions=True)


@router.post("/devserver/start", response_model=DevServerResponse)
async def start_devserver(req: DevServerStartRequest):
    root = Path(req.workspace).resolve()
    root.mkdir(parents=True, exist_ok=True)
    normalized = StartupManager.normalize_framework(req.framework, req.project_type, root)

    logging.info(
        "[devserver/start] cwd=%s workspace=%s resolved=%s framework=%s project_type=%s normalized=%s",
        os.getcwd(),
        req.workspace,
        root,
        req.framework,
        req.project_type,
        normalized,
    )

    ok, missing = StartupManager.preflight(normalized)
    if not ok:
        logging.warning("[devserver/start] preflight failed: %s", missing)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_environment",
                "message": "; ".join(missing),
                "framework": normalized,
                "workspace": str(root),
            },
        )
    if normalized == "wechat_miniprogram":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "wechat_devtools_required",
                "message": "WeChat MiniProgram preview requires WeChat DevTools. Please open this workspace in DevTools.",
                "workspace": str(root),
            },
        )
    ensure_entrypoint_alignment(root, normalized, max_depth=10)
    entry = detect_entrypoint(root, normalized)
    logging.info("[devserver/start] entry detection: root=%s fw=%s entry=%s", root, normalized, entry)
    if entry is None:
        repair_workspace_layout(root, max_depth=10)
        ensure_entrypoint_alignment(root, normalized, max_depth=10)
        entry = detect_entrypoint(root, normalized)
        logging.info("[devserver/start] after repair: entry=%s", entry)
    if entry is None:
        try:
            contents = list(root.iterdir())[:20]
            logging.error("[devserver/start] entry_point_missing - dir contents: %s", contents)
        except Exception as exc:
            logging.error("[devserver/start] failed to list dir: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "entry_point_missing",
                "message": f"No entry point found for framework '{normalized}' in workspace root.",
                "workspace": str(root),
            },
        )
    info = DevServerManager.start(
        workspace=req.workspace,
        framework=normalized,
        project_type=req.project_type,
        port=req.port,
        command=req.command,
    )
    health = await _health_with_config(info.url)
    if health.get("healthy") is not True and normalized in {"html", "general", "react", "vue", "nextjs", "uniapp"}:
        logging.warning("[devserver/start] primary health failed (%s), trying static fallback", health.get("reason"))
        try:
            DevServerManager.stop(workspace=req.workspace, framework=normalized)
            info = DevServerManager.start(
                workspace=req.workspace,
                framework=normalized,
                project_type=req.project_type,
                port=info.port,
                command=_static_fallback_command(root, info.port),
            )
            health = await _health_with_config(info.url)
            logging.info("[devserver/start] static fallback health=%s", health.get("reason"))
        except Exception as exc:
            logging.warning("[devserver/start] static fallback failed: %s", exc)
    return DevServerResponse(
        url=info.url,
        command=info.command,
        port=info.port,
        pid=info.pid,
        preview_health=health,
    )


@router.post("/devserver/stop")
async def stop_devserver(req: DevServerStopRequest):
    root = Path(req.workspace).resolve()
    normalized = StartupManager.normalize_framework(req.framework, req.project_type, root)
    stopped = DevServerManager.stop(workspace=req.workspace, framework=normalized)
    return {"stopped": stopped}


@router.post("/devserver/status")
async def status_devserver(req: DevServerStatusRequest):
    root = Path(req.workspace).resolve()
    normalized = StartupManager.normalize_framework(req.framework, req.project_type, root)
    status = DevServerManager.status(workspace=req.workspace, framework=normalized)
    info = status.get("info") if isinstance(status, dict) else None
    if isinstance(info, dict):
        health = await await_preview_health(str(info.get("url") or ""))
        status["preview_health"] = health
    else:
        status["preview_health"] = {"healthy": False, "reason": "server_not_running"}
    return status


@router.post("/devserver/restart", response_model=DevServerResponse)
async def restart_devserver(req: DevServerRestartRequest):
    root = Path(req.workspace).resolve()
    root.mkdir(parents=True, exist_ok=True)
    normalized = StartupManager.normalize_framework(req.framework, req.project_type, root)

    logging.info(
        "[devserver/restart] cwd=%s workspace=%s resolved=%s framework=%s project_type=%s normalized=%s",
        os.getcwd(),
        req.workspace,
        root,
        req.framework,
        req.project_type,
        normalized,
    )

    ok, missing = StartupManager.preflight(normalized)
    if not ok:
        logging.warning("[devserver/restart] preflight failed: %s", missing)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_environment",
                "message": "; ".join(missing),
                "framework": normalized,
                "workspace": str(root),
            },
        )
    if normalized == "wechat_miniprogram":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "wechat_devtools_required",
                "message": "WeChat MiniProgram preview requires WeChat DevTools. Please open this workspace in DevTools.",
                "workspace": str(root),
            },
        )
    ensure_entrypoint_alignment(root, normalized, max_depth=10)
    entry = detect_entrypoint(root, normalized)
    logging.info("[devserver/restart] entry detection: root=%s fw=%s entry=%s", root, normalized, entry)
    if entry is None:
        repair_workspace_layout(root, max_depth=10)
        ensure_entrypoint_alignment(root, normalized, max_depth=10)
        entry = detect_entrypoint(root, normalized)
        logging.info("[devserver/restart] after repair: entry=%s", entry)
    if entry is None:
        try:
            contents = list(root.iterdir())[:20]
            logging.error("[devserver/restart] entry_point_missing - dir contents: %s", contents)
        except Exception as exc:
            logging.error("[devserver/restart] failed to list dir: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "entry_point_missing",
                "message": f"No entry point found for framework '{normalized}' in workspace root.",
                "workspace": str(root),
            },
        )
    DevServerManager.stop(workspace=req.workspace, framework=normalized)
    info = DevServerManager.start(
        workspace=req.workspace,
        framework=normalized,
        project_type=req.project_type,
        port=req.port,
        command=req.command,
    )
    health = await _health_with_config(info.url)
    if health.get("healthy") is not True and normalized in {"html", "general", "react", "vue", "nextjs", "uniapp"}:
        logging.warning("[devserver/restart] primary health failed (%s), trying static fallback", health.get("reason"))
        try:
            DevServerManager.stop(workspace=req.workspace, framework=normalized)
            info = DevServerManager.start(
                workspace=req.workspace,
                framework=normalized,
                project_type=req.project_type,
                port=info.port,
                command=_static_fallback_command(root, info.port),
            )
            health = await _health_with_config(info.url)
            logging.info("[devserver/restart] static fallback health=%s", health.get("reason"))
        except Exception as exc:
            logging.warning("[devserver/restart] static fallback failed: %s", exc)
    return DevServerResponse(
        url=info.url,
        command=info.command,
        port=info.port,
        pid=info.pid,
        preview_health=health,
    )


@router.post("/devserver/logs")
async def devserver_logs(req: DevServerLogsRequest):
    framework = (req.framework or "").strip().lower()
    text = DevServerManager.log_tail(
        workspace=req.workspace,
        framework=framework,
        lines=max(20, min(int(req.lines), 1000)),
    )
    return {
        "workspace": req.workspace,
        "framework": framework,
        "lines": text.splitlines(),
        "text": text,
    }
