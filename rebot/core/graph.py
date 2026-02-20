"""Graph primitives for workflow execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    label: str | None = None


@dataclass
class Graph:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError("edge endpoints must exist")
        self.edges.append(edge)

    def to_mermaid(self) -> str:
        lines = ["graph TD;"]
        for node in self.nodes.values():
            lines.append(f"{node.id}[{node.label}]")
        for edge in self.edges:
            label = f"|{edge.label}|" if edge.label else ""
            lines.append(f"{edge.source} -->{label} {edge.target}")
        return "\n".join(lines)
