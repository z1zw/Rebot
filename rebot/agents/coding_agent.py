"""Coding task agent helper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rebot.agents.agent import Agent
from rebot.agents.middleware import AgentState
from rebot.agents.planning import PlanningMiddleware
from rebot.agents.reporting import ReportMiddleware
from rebot.agents.review import ReviewMiddleware
from rebot.agents.reasoning_chain import ReasoningChainMiddleware
from rebot.core.messages import Message
from rebot.models.base import ChatModel
from rebot.tools.fs_tools import (
    ApplyPatchTool,
    ListFilesTool,
    ReadFileTool,
    ReplaceInFileTool,
    WriteFileTool,
)
from rebot.tools.command_tool import RunTestsTool


@dataclass
class CodingAgent:
    model: ChatModel
    workspace_root: Path
    review_mode: bool = False
    report_filename: str = "rebot_report.md"
    graph_png_filename: str = "rebot_graph.png"
    mermaid_ink_url: str | None = "https://mermaid.ink"

    def build(self) -> Agent:
        tools = [
            ListFilesTool(),
            ReadFileTool(root=self.workspace_root),
            WriteFileTool(root=self.workspace_root),
            ReplaceInFileTool(root=self.workspace_root),
            ApplyPatchTool(root=self.workspace_root),
            RunTestsTool(root=self.workspace_root),
        ]
        report_path = self.workspace_root / self.report_filename
        graph_png_path = self.workspace_root / self.graph_png_filename
        middleware = [
            PlanningMiddleware(),
            ReasoningChainMiddleware(self.model),
            ReviewMiddleware(),
            ReportMiddleware(
                report_path=report_path,
                mermaid_png_path=graph_png_path,
                mermaid_ink_url=self.mermaid_ink_url,
            ),
        ]
        return Agent(model=self.model, tools=tools, middleware=middleware)

    def run_task(
        self,
        task: str,
        *,
        events: list[dict] | None = None,
        callbacks: object | None = None,
        stream_callback: callable | None = None,
        dialog_mode: str | None = None,
        attention: float | None = None,
        configurable: dict | None = None,
    ) -> AgentState:
        agent = self.build()
        if configurable is None:
            configurable = {}
        configurable.setdefault("tool_registry", agent.tools)
        system_parts = [
            "You are a coding agent. Use tools to inspect and edit files.",
            "Be precise and avoid unnecessary changes.",
        ]
        if dialog_mode:
            system_parts.append(f"Dialog mode: {dialog_mode}.")
        if attention is not None:
            system_parts.append(
                f"Attention level: {attention:.2f}. Allocate depth proportionally."
            )
        state = AgentState(
            messages=[
                Message(
                    role="system",
                    content=" ".join(system_parts),
                ),
                Message(role="user", content=task),
            ],
            review_mode=self.review_mode,
            events=events or [],
            configurable=configurable,
        )
        if callbacks is not None:
            state.callbacks = callbacks
        state.rc_stream_callback = stream_callback  # type: ignore[attr-defined]
        return agent.run(state, context=None)
