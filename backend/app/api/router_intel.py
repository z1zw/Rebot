from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.models import ASTIndexRequest, ASTSymbolRefsRequest
from app.intel.ast_index import ASTCodeIndexer


router = APIRouter()


@router.post("/intel/ast/index")
async def ast_index(req: ASTIndexRequest):
    root = Path(req.workspace).resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=400, detail="workspace_not_found")
    indexer = ASTCodeIndexer(
        root,
        max_files=max(1, min(int(req.max_files), 3000)),
        max_file_bytes=max(4096, min(int(req.max_file_bytes), 4 * 1024 * 1024)),
    )
    return indexer.build(include_references=bool(req.include_references))


@router.post("/intel/ast/references")
async def ast_references(req: ASTSymbolRefsRequest):
    root = Path(req.workspace).resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=400, detail="workspace_not_found")
    indexer = ASTCodeIndexer(
        root,
        max_files=max(1, min(int(req.max_files), 3000)),
        max_file_bytes=max(4096, min(int(req.max_file_bytes), 4 * 1024 * 1024)),
    )
    try:
        return indexer.find_references(
            symbol=req.symbol,
            include_definitions=bool(req.include_definitions),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
