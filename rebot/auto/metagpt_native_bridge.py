"""Bridge to run native MetaGPT multi-agent workflow from Rebot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import asyncio
import os
import sys
from typing import Any


@dataclass
class NativeMetaGPTResult:
    repo_path: str
    project_path: str
    rounds: int
    investment: float
    history_size: int
    total_cost: float


def run_native_metagpt(
    *,
    requirement: str,
    workspace: str,
    api_key: str,
    model: str,
    base_url: str,
    repo_path: str | None = None,
    rounds: int = 5,
    investment: float = 3.0,
) -> NativeMetaGPTResult:
    resolved_repo = _resolve_repo_path(repo_path)
    _ensure_sys_path(resolved_repo)

    from metagpt.config2 import Config
    from metagpt.context import Context
    from metagpt.roles import Architect, DataAnalyst, Engineer2, ProductManager, TeamLeader
    from metagpt.team import Team

    llm_config = {
        "api_type": _infer_api_type(base_url=base_url, model=model),
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
    }
    config = Config.from_llm_config(llm_config)
    config.update_via_cli(
        project_path=workspace,
        project_name=Path(workspace).name,
        inc=True,
        reqa_file="",
        max_auto_summarize_code=0,
    )
    ctx = Context(config=config)

    # Use local environment instead of MGX cloud runtime.
    company = Team(context=ctx, use_mgx=False)
    company.hire(
        [
            TeamLeader(),
            ProductManager(),
            Architect(),
            Engineer2(),
            DataAnalyst(),
        ]
    )
    company.invest(float(investment))
    asyncio.run(company.run(n_round=int(rounds), idea=requirement, auto_archive=False))

    history_size = len(company.env.history)
    total_cost = float(getattr(ctx.cost_manager, "total_cost", 0.0) or 0.0)
    return NativeMetaGPTResult(
        repo_path=str(resolved_repo),
        project_path=str(config.project_path or workspace),
        rounds=int(rounds),
        investment=float(investment),
        history_size=history_size,
        total_cost=total_cost,
    )


def _resolve_repo_path(repo_path: str | None) -> Path:
    candidates: list[Path] = []
    if repo_path:
        candidates.append(Path(repo_path))
    env_repo = os.getenv("METAGPT_REPO_PATH")
    if env_repo:
        candidates.append(Path(env_repo))
    # User-provided known path.
    candidates.append(Path(r"C:\Users\16320\Desktop\Experiments\Agnet\MetaGPT"))
    # Common sibling paths.
    candidates.append(Path.cwd().parent / "MetaGPT")
    candidates.append(Path.cwd() / "MetaGPT")

    for path in candidates:
        if path.exists() and (path / "metagpt").exists():
            return path.resolve()
    searched = ", ".join(str(p) for p in candidates)
    raise RuntimeError(f"MetaGPT repo not found. Searched: {searched}")


def _ensure_sys_path(repo: Path) -> None:
    repo_str = str(repo)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)


def _infer_api_type(*, base_url: str, model: str) -> str:
    low_base = (base_url or "").lower()
    low_model = (model or "").lower()
    if "deepseek" in low_base or low_model.startswith("deepseek-"):
        return "deepseek"
    if "moonshot" in low_base or low_model.startswith("moonshot-"):
        return "moonshot"
    if "anthropic" in low_base or low_model.startswith("claude-"):
        return "claude"
    return "openai"

