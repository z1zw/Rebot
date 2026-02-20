from __future__ import annotations

import asyncio
import re
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.process_sandbox import run_checked

router = APIRouter()


class GitDiffRequest(BaseModel):
    workspace: str
    path: str | None = None
    staged: bool = False
    ref: str | None = None


class GitStageRequest(BaseModel):
    workspace: str
    paths: list[str] = []


class GitUnstageRequest(BaseModel):
    workspace: str
    paths: list[str] = []


class GitCommitRequest(BaseModel):
    workspace: str
    message: str


class GitCheckoutRequest(BaseModel):
    workspace: str
    branch: str
    create: bool = False


class GitPullRequest(BaseModel):
    workspace: str
    rebase: bool = False


class GitPushRequest(BaseModel):
    workspace: str
    set_upstream: bool = False
    branch: str | None = None


def _normalize_workspace(workspace: str) -> Path:
    ws = Path((workspace or "").strip()).expanduser().resolve()
    if not ws.exists() or not ws.is_dir():
        raise ValueError(f"invalid_workspace:{ws}")
    return ws


async def _run_git(workspace: Path, args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    cmd = ["git", *args]
    return await asyncio.to_thread(
        run_checked,
        cmd,
        cwd=workspace,
        timeout=timeout,
        capture_output=True,
        text=True,
    )


async def _ensure_git_repo(workspace: str) -> Path:
    ws = _normalize_workspace(workspace)
    probe = await _run_git(ws, ["rev-parse", "--show-toplevel"])
    if probe.returncode != 0:
        err = (probe.stderr or probe.stdout or "").strip()
        raise ValueError(f"not_git_repo:{err or ws}")
    root = (probe.stdout or "").strip()
    return Path(root).resolve() if root else ws


def _parse_branch_line(line: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"branch": "", "upstream": "", "ahead": 0, "behind": 0}
    if not line.startswith("## "):
        return payload
    body = line[3:].strip()
    head, _, rest = body.partition("...")
    payload["branch"] = head.strip()
    if rest:
        upstream, _, flags = rest.partition(" ")
        payload["upstream"] = upstream.strip()
        if flags:
            ahead_m = re.search(r"ahead (\d+)", flags)
            behind_m = re.search(r"behind (\d+)", flags)
            payload["ahead"] = int(ahead_m.group(1)) if ahead_m else 0
            payload["behind"] = int(behind_m.group(1)) if behind_m else 0
    return payload


def _parse_status_line(line: str) -> dict[str, Any] | None:
    if len(line) < 4:
        return None
    code = line[:2]
    rest = line[3:].strip()
    if not rest:
        return None
    path = rest
    renamed_from = None
    if " -> " in rest:
        left, right = rest.split(" -> ", 1)
        renamed_from = left.strip()
        path = right.strip()
    x, y = code[0], code[1]
    return {
        "path": path,
        "renamed_from": renamed_from,
        "index_status": x,
        "worktree_status": y,
        "staged": x not in {" ", "?"},
        "unstaged": y != " ",
        "untracked": code == "??",
        "deleted": x == "D" or y == "D",
        "renamed": x == "R",
    }


@router.get("/git/status")
async def git_status(workspace: str):
    try:
        root = await _ensure_git_repo(workspace)
        proc = await _run_git(root, ["status", "--porcelain=1", "--branch"])
        if proc.returncode != 0:
            return {"ok": False, "error": (proc.stderr or proc.stdout or "status_failed").strip()}
        lines = [x for x in (proc.stdout or "").splitlines() if x.strip()]
        branch_info = _parse_branch_line(lines[0]) if lines else {"branch": "", "upstream": "", "ahead": 0, "behind": 0}
        files = [parsed for line in lines[1:] if (parsed := _parse_status_line(line))]
        return {
            "ok": True,
            "root": str(root),
            "branch": branch_info["branch"],
            "upstream": branch_info["upstream"],
            "ahead": branch_info["ahead"],
            "behind": branch_info["behind"],
            "is_clean": len(files) == 0,
            "count": len(files),
            "files": files,
        }
    except FileNotFoundError:
        return {"ok": False, "error": "git_not_found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/git/branches")
async def git_branches(workspace: str):
    try:
        root = await _ensure_git_repo(workspace)
        proc = await _run_git(root, ["branch", "--format=%(refname:short)|%(upstream:short)|%(HEAD)"])
        if proc.returncode != 0:
            return {"ok": False, "error": (proc.stderr or proc.stdout or "branches_failed").strip()}
        branches: list[dict[str, Any]] = []
        for line in (proc.stdout or "").splitlines():
            if not line.strip():
                continue
            parts = line.split("|")
            name = (parts[0] if len(parts) > 0 else "").strip()
            upstream = (parts[1] if len(parts) > 1 else "").strip()
            head = (parts[2] if len(parts) > 2 else "").strip()
            branches.append(
                {
                    "name": name,
                    "upstream": upstream,
                    "current": head == "*",
                }
            )
        return {"ok": True, "branches": branches}
    except FileNotFoundError:
        return {"ok": False, "error": "git_not_found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/git/log")
async def git_log(workspace: str, limit: int = 30):
    try:
        root = await _ensure_git_repo(workspace)
        n = max(1, min(int(limit), 200))
        proc = await _run_git(
            root,
            ["log", f"--max-count={n}", "--date=iso", r"--pretty=format:%H%x1f%h%x1f%an%x1f%ad%x1f%s"],
        )
        if proc.returncode != 0:
            return {"ok": False, "error": (proc.stderr or proc.stdout or "log_failed").strip()}
        commits: list[dict[str, str]] = []
        for line in (proc.stdout or "").splitlines():
            if not line.strip():
                continue
            parts = line.split("\x1f")
            if len(parts) < 5:
                continue
            commits.append(
                {
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "author": parts[2],
                    "date": parts[3],
                    "subject": parts[4],
                }
            )
        return {"ok": True, "commits": commits}
    except FileNotFoundError:
        return {"ok": False, "error": "git_not_found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/git/diff")
async def git_diff(req: GitDiffRequest):
    try:
        root = await _ensure_git_repo(req.workspace)
        if req.ref and req.ref.strip():
            args = ["show", "--no-color", "--stat", "--patch", req.ref.strip()]
        else:
            args = ["diff", "--no-color"]
            if req.staged:
                args.append("--staged")
            if req.path and req.path.strip():
                args += ["--", req.path.strip()]
        proc = await _run_git(root, args, timeout=60)
        if proc.returncode != 0:
            return {"ok": False, "error": (proc.stderr or proc.stdout or "diff_failed").strip()}
        text = (proc.stdout or "")[:200000]
        return {"ok": True, "diff": text}
    except FileNotFoundError:
        return {"ok": False, "error": "git_not_found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/git/stage")
async def git_stage(req: GitStageRequest):
    try:
        root = await _ensure_git_repo(req.workspace)
        args = ["add", "-A"] if not req.paths else ["add", "--", *[p.strip() for p in req.paths if p.strip()]]
        proc = await _run_git(root, args, timeout=45)
        if proc.returncode != 0:
            return {"ok": False, "error": (proc.stderr or proc.stdout or "stage_failed").strip()}
        return {"ok": True}
    except FileNotFoundError:
        return {"ok": False, "error": "git_not_found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/git/unstage")
async def git_unstage(req: GitUnstageRequest):
    try:
        root = await _ensure_git_repo(req.workspace)
        args = ["restore", "--staged", "."] if not req.paths else ["restore", "--staged", "--", *[p.strip() for p in req.paths if p.strip()]]
        proc = await _run_git(root, args, timeout=45)
        if proc.returncode != 0:
            return {"ok": False, "error": (proc.stderr or proc.stdout or "unstage_failed").strip()}
        return {"ok": True}
    except FileNotFoundError:
        return {"ok": False, "error": "git_not_found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/git/commit")
async def git_commit(req: GitCommitRequest):
    try:
        root = await _ensure_git_repo(req.workspace)
        msg = (req.message or "").strip()
        if not msg:
            return {"ok": False, "error": "commit_message_required"}
        proc = await _run_git(root, ["commit", "-m", msg], timeout=90)
        if proc.returncode != 0:
            return {"ok": False, "error": (proc.stderr or proc.stdout or "commit_failed").strip()}
        tail = await _run_git(
            root,
            ["log", "--max-count=1", r"--pretty=format:%H%x1f%h%x1f%an%x1f%ad%x1f%s"],
            timeout=15,
        )
        latest: dict[str, str] | None = None
        line = (tail.stdout or "").strip()
        if line:
            parts = line.split("\x1f")
            if len(parts) >= 5:
                latest = {
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "author": parts[2],
                    "date": parts[3],
                    "subject": parts[4],
                }
        return {"ok": True, "commit": latest}
    except FileNotFoundError:
        return {"ok": False, "error": "git_not_found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/git/checkout")
async def git_checkout(req: GitCheckoutRequest):
    try:
        root = await _ensure_git_repo(req.workspace)
        branch = (req.branch or "").strip()
        if not branch:
            return {"ok": False, "error": "branch_required"}
        args = ["switch", "-c", branch] if req.create else ["switch", branch]
        proc = await _run_git(root, args, timeout=45)
        if proc.returncode != 0:
            fallback = await _run_git(root, ["checkout", "-b", branch] if req.create else ["checkout", branch], timeout=45)
            if fallback.returncode != 0:
                return {"ok": False, "error": (fallback.stderr or fallback.stdout or "checkout_failed").strip()}
        return {"ok": True, "branch": branch}
    except FileNotFoundError:
        return {"ok": False, "error": "git_not_found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/git/pull")
async def git_pull(req: GitPullRequest):
    try:
        root = await _ensure_git_repo(req.workspace)
        args = ["pull", "--rebase"] if req.rebase else ["pull"]
        proc = await _run_git(root, args, timeout=180)
        if proc.returncode != 0:
            return {"ok": False, "error": (proc.stderr or proc.stdout or "pull_failed").strip()}
        return {"ok": True, "stdout": (proc.stdout or "").strip()[-4000:]}
    except FileNotFoundError:
        return {"ok": False, "error": "git_not_found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/git/push")
async def git_push(req: GitPushRequest):
    try:
        root = await _ensure_git_repo(req.workspace)
        args = ["push"]
        if req.set_upstream and req.branch and req.branch.strip():
            args += ["-u", "origin", req.branch.strip()]
        proc = await _run_git(root, args, timeout=180)
        if proc.returncode != 0:
            return {"ok": False, "error": (proc.stderr or proc.stdout or "push_failed").strip()}
        return {"ok": True, "stdout": (proc.stdout or "").strip()[-4000:]}
    except FileNotFoundError:
        return {"ok": False, "error": "git_not_found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
