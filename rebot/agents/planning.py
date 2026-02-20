"""Planning helpers and middleware."""

from __future__ import annotations

from dataclasses import dataclass

from rebot.agents.middleware import AgentState
from rebot.core.messages import Message


def simple_plan(task: str) -> list[str]:
    steps = [
        "Inspect relevant files and project structure.",
        "Identify required changes and constraints.",
        "Apply minimal code changes.",
        "Run tests or validate behavior.",
        "Summarize changes and risks.",
    ]
    return steps if task else steps


@dataclass
class PlanningMiddleware:
    def before_agent(self, state: AgentState, context) -> dict[str, object] | None:
        if state.plan:
            return None
        task = ""
        for msg in state.messages:
            if msg.role == "user":
                task = msg.content
        plan = simple_plan(task)
        plan_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
        state.messages.insert(
            0,
            Message(
                role="system",
                content=f"Execution plan:\n{plan_text}\nFollow the plan strictly.",
            ),
        )
        return {"plan": plan}
