"""Code review mode middleware."""

from __future__ import annotations

from dataclasses import dataclass

from rebot.agents.middleware import AgentState
from rebot.core.messages import Message


@dataclass
class ReviewMiddleware:
    def before_model(self, state: AgentState, context) -> dict[str, object] | None:
        if not state.review_mode:
            return None
        instructions = (
            "You are in code review mode. "
            "Focus on correctness, regressions, missing tests, and risky changes. "
            "Summarize findings and residual risks."
        )
        state.messages.insert(0, Message(role="system", content=instructions))
        return None

    def after_agent(self, state: AgentState, context) -> dict[str, object] | None:
        if not state.review_mode:
            return None
        for msg in reversed(state.messages):
            if msg.role == "assistant":
                return {"review_report": msg.content}
        return None
