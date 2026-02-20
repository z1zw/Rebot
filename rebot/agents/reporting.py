"""Change reporting and graph rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import base64

from rebot.agents.middleware import AgentState
from rebot.core.graph import Edge, Graph, Node
from rebot.tools.mermaid import render_mermaid_png


def build_execution_graph(state: AgentState) -> Graph:
    graph = Graph()
    graph.add_node(Node(id="start", label="Start"))
    last = "start"
    for idx, step in enumerate(state.plan):
        node_id = f"plan_{idx+1}"
        graph.add_node(Node(id=node_id, label=step))
        graph.add_edge(Edge(source=last, target=node_id))
        last = node_id
    if state.change_log:
        graph.add_node(Node(id="changes", label="Changes"))
        graph.add_edge(Edge(source=last, target="changes"))
        last = "changes"
    graph.add_node(Node(id="end", label="End"))
    graph.add_edge(Edge(source=last, target="end"))
    return graph


def generate_change_report(state: AgentState) -> str:
    lines: list[str] = []
    if state.plan:
        lines.append("Plan:")
        lines.extend(f"- {step}" for step in state.plan)
    if state.change_log:
        lines.append("Changes:")
        lines.extend(f"- {entry}" for entry in state.change_log)
    else:
        lines.append("Changes: none recorded.")
    if state.review_report:
        lines.append("Review:")
        lines.append(state.review_report)
    lines.append("Risks:")
    lines.append("- Verify tests were executed and passed.")
    return "\n".join(lines)


@dataclass
class ReportMiddleware:
    report_path: Path | None = None
    mermaid_png_path: Path | None = None
    mermaid_ink_url: str | None = None

    def after_agent(self, state: AgentState, context) -> dict[str, object] | None:
        graph = build_execution_graph(state)
        report = generate_change_report(state)
        mermaid_text = graph.to_mermaid()
        png_path_str = None
        if self.mermaid_png_path is not None and self.mermaid_ink_url is not None:
            png_path_str = str(self.mermaid_png_path)
            try:
                render_mermaid_png(mermaid_text, self.mermaid_png_path, self.mermaid_ink_url)
            except Exception:
                png_path_str = None
        if self.report_path is not None:
            self.report_path.parent.mkdir(parents=True, exist_ok=True)
            self.report_path.write_text(
                f"{report}\n\n```mermaid\n{mermaid_text}\n```\n",
                encoding="utf-8",
            )
        return {
            "execution_graph_mermaid": graph.to_mermaid(),
            "execution_graph_png": png_path_str,
            "report": report,
        }
