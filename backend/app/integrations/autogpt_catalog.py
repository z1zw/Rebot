from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json


DEFAULT_AUTOGPT_ROOT = Path(r"C:\Users\16320\Desktop\Experiments\Agnet\AutoGPT")


@dataclass
class AutoGPTAgent:
    agent_id: str
    name: str
    description: str
    instructions: str
    source_path: str


def _agents_dir(root: Path | None = None) -> Path:
    base = (root or DEFAULT_AUTOGPT_ROOT).resolve()
    return base / "autogpt_platform" / "backend" / "agents"


def list_agents(root: Path | None = None, limit: int = 200) -> list[AutoGPTAgent]:
    agents_path = _agents_dir(root)
    if not agents_path.exists():
        return []
    out: list[AutoGPTAgent] = []
    for p in sorted(agents_path.glob("agent_*.json"))[: max(1, limit)]:
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        agent_id = str(raw.get("id") or p.stem)
        name = str(raw.get("name") or raw.get("title") or p.stem)
        description = str(raw.get("description") or "")
        instructions = str(raw.get("instructions") or raw.get("prompt") or "")
        out.append(
            AutoGPTAgent(
                agent_id=agent_id,
                name=name,
                description=description,
                instructions=instructions,
                source_path=str(p),
            )
        )
    return out


def get_agent(agent_id: str, root: Path | None = None) -> AutoGPTAgent | None:
    aid = (agent_id or "").strip()
    if not aid:
        return None
    for a in list_agents(root=root, limit=1000):
        if a.agent_id == aid:
            return a
        if Path(a.source_path).stem == aid:
            return a
    return None


def import_agent_to_workspace(agent_id: str, workspace: Path, root: Path | None = None) -> dict[str, Any]:
    agent = get_agent(agent_id, root=root)
    if agent is None:
        raise ValueError(f"AutoGPT agent not found: {agent_id}")
    ws = workspace.resolve()
    ws.mkdir(parents=True, exist_ok=True)
    target_dir = ws / ".rebot" / "autogpt_imports"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{agent.agent_id}.json"
    payload = {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "description": agent.description,
        "instructions": agent.instructions,
        "source_path": agent.source_path,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload

