"""AutoGPT-style iterative agent loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rebot.core.messages import Message
from rebot.models.base import ChatModel
from rebot.tools.base import BaseTool
from rebot.agents.agent import Agent
from rebot.agents.middleware import AgentState
from rebot.tools.fs_tools import ReadFileTool, ListFilesTool, WriteFileTool
from rebot.agents.vector_memory import VectorMemory, _hash_vector
from rebot.agents.pgvector_memory import PgVectorMemory


@dataclass
class Goal:
    text: str
    done: bool = False


@dataclass
class AutoGPTLoop:
    model: ChatModel
    goals: list[Goal]
    tools: list[BaseTool] = field(default_factory=list)
    max_iters: int = 6
    reflections: list[str] = field(default_factory=list)
    memory: list[str] = field(default_factory=list)
    memory_path: str | None = None
    vector_memory_path: str | None = None
    enable_vector_memory: bool = True
    vector_backend: str = "local"
    pgvector_dsn: str | None = None
    pgvector_table: str = "rebot_vector_memory"
    workspace: str | None = None
    critique: list[str] = field(default_factory=list)
    task_queue: list[str] = field(default_factory=list)
    auto_execute_queue: bool = True
    auto_fix: bool = True

    def run(self) -> AgentState:
        if self.memory_path:
            self._load_memory()
        if self.vector_memory_path and self.enable_vector_memory:
            self._load_vector_memory()
        tools = list(self.tools)
        if self.workspace:
            tools.extend(
                [
                    ListFilesTool(),
                    ReadFileTool(root=_path(self.workspace)),
                    WriteFileTool(root=_path(self.workspace)),
                ]
            )
        agent = Agent(model=self.model, tools=tools, middleware=[])
        state = AgentState(
            messages=[
                Message(
                    role="system",
                    content=(
                        "You are an AutoGPT-style agent. Iterate over goals and complete them. "
                        "Use tools to inspect and modify workspace when helpful."
                    ),
                ),
                Message(
                    role="system",
                    content=self._memory_prompt(),
                ),
                Message(
                    role="system",
                    content=self._long_term_prompt(self._goal_prompt()),
                ),
                Message(role="user", content=self._goal_prompt()),
            ],
        )
        for _ in range(self.max_iters):
            result = agent.run(state, context=None)
            last = result.messages[-1]
            self.reflections.append(last.content[:300])
            self._update_memory(last.content)
            self._update_queue(last.content)
            self._self_critique(last.content)
            if self.auto_execute_queue:
                self._execute_queue(agent, state)
            if self.auto_fix:
                self._auto_fix(agent, state)
            self._mark_done(last.content)
            if all(g.done for g in self.goals):
                break
            state.messages.append(
                Message(role="user", content=self._goal_prompt())
            )
        return state

    def _goal_prompt(self) -> str:
        items = "\n".join(
            f"- [{'x' if g.done else ' '}] {g.text}" for g in self.goals
        )
        return f"Goals:\n{items}\n\nUpdate progress and take next action."

    def _memory_prompt(self) -> str:
        if not self.memory:
            return "No prior memory."
        recent = "\n".join(self.memory[-6:])
        return "Prior memory (use to avoid repeats):\n" + recent

    def _mark_done(self, content: str) -> None:
        for g in self.goals:
            if g.text.lower() in content.lower():
                g.done = True

    def _update_memory(self, content: str) -> None:
        self.memory.append(content[:400])
        if len(self.memory) > 20:
            self.memory = self.memory[-20:]
        if self.memory_path:
            self._save_memory()
        if self.enable_vector_memory:
            self._update_vector_memory(content)

    def _self_critique(self, content: str) -> None:
        prompt = (
            "Provide a brief self-critique of the previous response. "
            "Focus on missing steps and risks."
        )
        msg = self.model.invoke([Message(role="user", content=f"{prompt}\n\n{content}")], tools=[])
        self.critique.append(msg.content[:300])

    def _update_queue(self, content: str) -> None:
        if "next:" in content.lower():
            self.task_queue.append(content[:200])

    def _execute_queue(self, agent: Agent, state: AgentState) -> None:
        if not self.task_queue:
            return
        task = self.task_queue.pop(0)
        state.messages.append(
            Message(role="user", content=f"Execute queued task:\n{task}")
        )
        agent.run(state, context=None)

    def _auto_fix(self, agent: Agent, state: AgentState) -> None:
        if not self.critique:
            return
        issue = self.critique[-1]
        state.messages.append(
            Message(role="user", content=f"Fix the issues based on critique:\n{issue}")
        )
        agent.run(state, context=None)

    def _save_memory(self) -> None:
        from pathlib import Path
        import json

        path = Path(self.memory_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"memory": self.memory, "reflections": self.reflections, "critique": self.critique}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_memory(self) -> None:
        from pathlib import Path
        import json

        path = Path(self.memory_path)
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self.memory = list(data.get("memory", self.memory))
        self.reflections = list(data.get("reflections", self.reflections))
        self.critique = list(data.get("critique", self.critique))

    def _load_vector_memory(self) -> None:
        if self.vector_memory_path is None:
            if self.vector_backend != "pgvector":
                return
        if self.vector_backend == "pgvector":
            if not self.pgvector_dsn:
                return
            self._pg = PgVectorMemory(self.pgvector_dsn, table=self.pgvector_table)
            self._pg.init()
            return
        self._vector = VectorMemory(_path(self.vector_memory_path))
        self._vector.load()

    def _update_vector_memory(self, content: str) -> None:
        if self.vector_backend == "pgvector":
            if not self.pgvector_dsn:
                return
            pg = getattr(self, "_pg", None)
            if pg is None:
                self._pg = PgVectorMemory(self.pgvector_dsn, table=self.pgvector_table)
                pg = self._pg
            embedding = _hash_vector(content)
            pg.add(content, embedding, metadata={"source": "autogpt_loop"})
            return
        vector = getattr(self, "_vector", None)
        if vector is None:
            if self.vector_memory_path is None:
                return
            self._vector = VectorMemory(_path(self.vector_memory_path))
            vector = self._vector
        vector.add(content, metadata={"source": "autogpt_loop"})
        vector.save()

    def _long_term_prompt(self, query: str) -> str:
        if self.vector_backend == "pgvector":
            if not self.pgvector_dsn:
                return "No long-term memory."
            pg = getattr(self, "_pg", None)
            if pg is None:
                self._pg = PgVectorMemory(self.pgvector_dsn, table=self.pgvector_table)
                pg = self._pg
            hits = pg.search(_hash_vector(query), top_k=4)
        else:
            vector = getattr(self, "_vector", None)
            if vector is None:
                return "No long-term memory."
            hits = vector.search(query, top_k=4)
        if not hits:
            return "No long-term memory."
        snippets = "\n".join(f"- {h['text'][:200]}" for h in hits)
        return "Long-term memory (similar tasks):\n" + snippets


def _path(raw: str):
    from pathlib import Path

    return Path(raw)
