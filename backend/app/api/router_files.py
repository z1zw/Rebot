from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.models import (
    FileDeleteRequest,
    FileListRequest,
    FileReadRequest,
    FileRepairRequest,
    FileWriteRequest,
)
from app.api.services.workspace_service import (
    normalize_and_validate_path,
    repair_workspace_layout,
    safe_join_workspace,
)
from rebot.tools.fs_tools import ListFilesTool, ReadFileTool, WriteFileTool


router = APIRouter()


@router.post("/files/list")
async def list_files(req: FileListRequest):
    tool = ListFilesTool()
    content = tool.run({"path": req.workspace, "max_depth": req.max_depth})
    files = [line for line in content.splitlines() if line]
    resolved = str(Path(req.workspace).resolve())
    if not req.tree:
        return {"files": files, "workspace_resolved": resolved}
    return {"tree": _build_tree(files), "workspace_resolved": resolved}


@router.post("/files/repair")
async def repair_files(req: FileRepairRequest):
    root = Path(req.workspace).resolve()
    result = repair_workspace_layout(root, max_depth=max(2, min(int(req.max_depth), 16)))
    tool = ListFilesTool()
    content = tool.run({"path": str(root), "max_depth": 8})
    files = [line for line in content.splitlines() if line]
    result["files"] = files
    return result


@router.post("/files/read")
async def read_file(req: FileReadRequest):
    try:
        root = Path(req.workspace).resolve()
        _, norm_path = normalize_and_validate_path(root, req.path)
        tool = ReadFileTool(root=root)
        content = tool.run({"path": norm_path})
        return {"content": content}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/files/write")
async def write_file(req: FileWriteRequest):
    try:
        root = Path(req.workspace).resolve()
        _, norm_path = normalize_and_validate_path(root, req.path)
        tool = WriteFileTool(root=root)
        result = tool.run({"path": norm_path, "content": req.content})
        return {"result": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/files/delete")
async def delete_file(req: FileDeleteRequest):
    try:
        root = Path(req.workspace).resolve()
        target = safe_join_workspace(root, req.path)
        if not target.exists():
            return {"deleted": False, "error": "not_found"}
        if target.is_dir():
            try:
                target.rmdir()
            except OSError:
                return {"deleted": False, "error": "dir_not_empty"}
        else:
            target.unlink()
        return {"deleted": True, "path": req.path}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _build_tree(files: list[str]) -> dict[str, Any]:
    root: dict[str, Any] = {}
    for path in files:
        parts = path.replace("\\", "/").split("/")
        node = root
        for idx, part in enumerate(parts):
            if idx == len(parts) - 1:
                node.setdefault("files", []).append(part)
            else:
                node = node.setdefault(part, {})
    return root
