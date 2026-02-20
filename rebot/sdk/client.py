"""SDK client entrypoint."""

from __future__ import annotations

from rebot.agents.agent import Agent
from rebot.agents.middleware import AgentState


class RebotClient:
    def __init__(self, agent: Agent) -> None:
        self.agent = agent

    def run(self, messages: list[dict[str, str]]) -> AgentState:
        state = AgentState(messages=[self._to_message(m) for m in messages])
        return self.agent.run(state, context=None)

    async def run_async(self, messages: list[dict[str, str]]) -> AgentState:
        state = AgentState(messages=[self._to_message(m) for m in messages])
        return await self.agent.run_async(state, context=None)

    def _to_message(self, raw: dict[str, str]):
        from rebot.core.messages import Message

        return Message(role=raw["role"], content=raw["content"])
