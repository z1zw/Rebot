from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable
import asyncio
import json
from collections import defaultdict, deque

from app.integrations.autogpt_catalog import get_agent, DEFAULT_AUTOGPT_ROOT


Emit = Callable[[str, Any], Awaitable[None]]


@dataclass
class WorkflowAnalysis:
    agent_id: str
    name: str
    node_count: int
    edge_count: int
    levels: list[list[str]]
    inferred_files: list[str]
    summary: str


def _load_agent_json(agent_id: str, root: Path | None = None) -> dict[str, Any]:
    agent = get_agent(agent_id, root=root)
    if agent is None:
        raise ValueError(f"AutoGPT agent not found: {agent_id}")
    source = Path(agent.source_path)
    raw = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Invalid AutoGPT agent json")
    return raw


def _infer_files(nodes: list[dict[str, Any]]) -> list[str]:
    out: set[str] = set()
    exts = (".py", ".js", ".ts", ".tsx", ".jsx", ".dart", ".html", ".css", ".json", ".md", ".yaml", ".yml")
    for n in nodes:
        defaults = n.get("input_default")
        if isinstance(defaults, dict):
            for v in defaults.values():
                s = str(v or "").strip()
                if "/" in s or "\\" in s:
                    low = s.lower()
                    if any(low.endswith(ext) for ext in exts):
                        out.add(s.replace("\\", "/"))
    return sorted(out)


def analyze_agent_workflow(agent_id: str, root: Path | None = None) -> WorkflowAnalysis:
    raw = _load_agent_json(agent_id, root=root)
    nodes_raw = raw.get("nodes")
    nodes: list[dict[str, Any]] = [n for n in nodes_raw if isinstance(n, dict)] if isinstance(nodes_raw, list) else []
    node_ids = {str(n.get("id")) for n in nodes if n.get("id")}
    indeg: dict[str, int] = {nid: 0 for nid in node_ids}
    adj: dict[str, list[str]] = defaultdict(list)
    edges = 0

    for n in nodes:
        outs = n.get("output_links")
        if not isinstance(outs, list):
            continue
        for link in outs:
            if not isinstance(link, dict):
                continue
            s = str(link.get("source_id") or "")
            t = str(link.get("sink_id") or "")
            if s in node_ids and t in node_ids:
                adj[s].append(t)
                indeg[t] += 1
                edges += 1

    q = deque([nid for nid, d in indeg.items() if d == 0])
    levels: list[list[str]] = []
    seen = 0
    while q:
        size = len(q)
        layer: list[str] = []
        for _ in range(size):
            u = q.popleft()
            layer.append(u)
            seen += 1
            for v in adj.get(u, []):
                indeg[v] -= 1
                if indeg[v] == 0:
                    q.append(v)
        if layer:
            levels.append(layer)

    # cycle fallback: put remaining nodes into one level
    if seen < len(node_ids):
        rem = [nid for nid, d in indeg.items() if d > 0]
        if rem:
            levels.append(rem)

    inferred_files = _infer_files(nodes)
    summary = (
        f"AutoGPT workflow: {raw.get('name', 'unknown')} | "
        f"nodes={len(nodes)} edges={edges} levels={len(levels)} inferred_files={len(inferred_files)}"
    )
    return WorkflowAnalysis(
        agent_id=str(raw.get("id") or agent_id),
        name=str(raw.get("name") or "AutoGPT Workflow"),
        node_count=len(nodes),
        edge_count=edges,
        levels=levels,
        inferred_files=inferred_files,
        summary=summary,
    )


async def execute_workflow_trace(
    *,
    agent_id: str,
    emit: Emit,
    root: Path | None = None,
    max_concurrency: int = 10,
) -> WorkflowAnalysis:
    analysis = analyze_agent_workflow(agent_id, root=root)
    await emit("console_log", {"text": f"[autogpt/workflow] {analysis.summary}", "level": "default"})
    sem = asyncio.Semaphore(max(1, min(max_concurrency, 32)))

    async def _run_node(node_id: str, level_idx: int) -> None:
        async with sem:
            await emit(
                "agent_message",
                {
                    "agent": "AutoGPTAdapter",
                    "role": "Workflow",
                    "content": f"[L{level_idx}] executing node {node_id}",
                    "step": level_idx + 1,
                    "total_steps": max(1, len(analysis.levels)),
                },
            )
            await asyncio.sleep(0.01)

    for idx, layer in enumerate(analysis.levels):
        await emit("console_log", {"text": f"[autogpt/workflow] level {idx}: {len(layer)} node(s)", "level": "info"})
        await asyncio.gather(*(_run_node(nid, idx) for nid in layer))
    return analysis

