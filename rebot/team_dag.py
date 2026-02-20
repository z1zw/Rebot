"""DAG-based multi-agent scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import asyncio

from rebot.environment.base import Environment
from rebot.roles.role import Role
from rebot.schema import RoutedMessage
from rebot.core.messages import Message


@dataclass
class TaskNode:
    id: str
    content: str
    role: str
    depends_on: list[str] = field(default_factory=list)


@dataclass
class TaskDAG:
    nodes: dict[str, TaskNode] = field(default_factory=dict)

    def add(self, node: TaskNode) -> None:
        self.nodes[node.id] = node

    def ready_nodes(self, completed: set[str]) -> list[TaskNode]:
        ready: list[TaskNode] = []
        for node in self.nodes.values():
            if node.id in completed:
                continue
            if all(dep in completed for dep in node.depends_on):
                ready.append(node)
        return ready


@dataclass
class TeamDAGScheduler:
    env: Environment
    max_rounds: int = 10

    def register(self, role: Role) -> None:
        self.env.register_role(role)

    async def run(self, dag: TaskDAG) -> None:
        completed: set[str] = set()
        for _ in range(self.max_rounds):
            ready = dag.ready_nodes(completed)
            if not ready:
                break
            await asyncio.gather(*(self._dispatch(node) for node in ready))
            await self._tick()
            completed.update(node.id for node in ready)

    async def _dispatch(self, node: TaskNode) -> None:
        if node.role not in self.env.roles:
            return
        self.env.publish(
            RoutedMessage(
                message=Message(role="user", content=node.content),
                sent_from="scheduler",
                send_to=[node.role],
                metadata={"task_id": node.id, "deps": node.depends_on},
            )
        )

    async def _tick(self) -> None:
        async def run_role(role: Role) -> None:
            if not role.is_idle():
                role.run(self.env)

        await asyncio.gather(*(run_role(r) for r in self.env.roles.values()))
