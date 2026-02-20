"""Concurrent team scheduler for roles."""

from __future__ import annotations

from dataclasses import dataclass, field
import asyncio
from typing import Any

from rebot.environment.base import Environment
from rebot.roles.role import Role
from rebot.schema import RoutedMessage
from rebot.core.messages import Message


@dataclass
class TeamScheduler:
    env: Environment
    max_rounds: int = 6

    def register(self, role: Role) -> None:
        self.env.register_role(role)

    async def run(self, task: str) -> None:
        self.env.publish(
            RoutedMessage(
                message=Message(role="user", content=task),
                sent_from="user",
                send_to=list(self.env.roles.keys()) or [],
            )
        )
        for _ in range(self.max_rounds):
            await self._tick()

    async def _tick(self) -> None:
        async def run_role(role: Role) -> None:
            if not role.is_idle():
                role.run(self.env)

        await asyncio.gather(*(run_role(r) for r in self.env.roles.values()))

