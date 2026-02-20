"""Graph-based agent runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any

from rebot.agents.middleware import AgentState
from rebot.core.graph import Edge, Graph, Node


NodeFn = Callable[[AgentState, Any], AgentState]
EdgeFn = Callable[[AgentState], str | None]


@dataclass
class GraphRuntime:
    graph: Graph | None
    nodes: dict[str, NodeFn]
    edges: dict[str, EdgeFn]
    entry: str
    end: str = "end"

    def run(self, state: AgentState, context: Any) -> AgentState:
        current = self.entry
        while True:
            if current == self.end:
                return state
            fn = self.nodes.get(current)
            if fn is None:
                raise ValueError(f"missing node: {current}")
            state = fn(state, context)
            edge_fn = self.edges.get(current)
            if edge_fn is None:
                raise ValueError(f"missing edge router: {current}")
            nxt = edge_fn(state)
            if nxt is None:
                return state
            current = nxt


def build_simple_agent_graph(entry: str = "before_agent") -> Graph:
    graph = Graph()
    graph.add_node(Node(id="before_agent", label="before_agent"))
    graph.add_node(Node(id="before_model", label="before_model"))
    graph.add_node(Node(id="model", label="model"))
    graph.add_node(Node(id="tools", label="tools"))
    graph.add_node(Node(id="after_model", label="after_model"))
    graph.add_node(Node(id="after_agent", label="after_agent"))
    graph.add_node(Node(id="end", label="end"))
    graph.add_edge(Edge(source="before_agent", target="before_model"))
    graph.add_edge(Edge(source="before_model", target="model"))
    graph.add_edge(Edge(source="model", target="after_model"))
    graph.add_edge(Edge(source="after_model", target="tools"))
    graph.add_edge(Edge(source="tools", target="before_model"))
    graph.add_edge(Edge(source="after_model", target="after_agent"))
    graph.add_edge(Edge(source="after_agent", target="end"))
    return graph
