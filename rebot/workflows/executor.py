"""Workflow executor."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from rebot.workflows.schema import INPUT_NODE, WorkflowResult, WorkflowSpec
from rebot.workflows.blocks.base import ExecutionContext
from rebot.workflows.registry import BlockRegistry


@dataclass
class WorkflowExecutor:
    registry: BlockRegistry
    ctx: ExecutionContext

    async def run(self, workflow: WorkflowSpec, inputs: dict[str, Any]) -> WorkflowResult:
        nodes = {node.id: node for node in workflow.nodes}
        incoming: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        outgoing: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        for edge in workflow.edges:
            incoming[edge.target].append((edge.source, edge.source_key, edge.target_key))
            outgoing[edge.source].append((edge.target, edge.source_key, edge.target_key))
        if workflow.entrypoint and workflow.entrypoint not in nodes:
            raise RuntimeError(f"Entrypoint {workflow.entrypoint} not found.")
        result = WorkflowResult()
        ready = deque()
        seen = set()
        order: list[str] = []

        def is_ready(node_id: str) -> bool:
            for source_id, _, _ in incoming.get(node_id, []):
                if source_id == INPUT_NODE:
                    continue
                if source_id not in result.node_outputs:
                    return False
            return True

        for node_id in nodes:
            if is_ready(node_id):
                ready.append(node_id)

        if workflow.entrypoint:
            ready = deque([workflow.entrypoint])

        while ready:
            node_id = ready.popleft()
            if node_id in seen:
                continue
            if not is_ready(node_id):
                continue
            node = nodes[node_id]
            block = self.registry.create(node.type, node.config)
            node_inputs: dict[str, Any] = {}
            for source_id, source_key, target_key in incoming.get(node_id, []):
                if source_id == INPUT_NODE:
                    node_inputs[target_key] = inputs.get(source_key)
                    continue
                node_inputs[target_key] = result.node_outputs[source_id].get(source_key)
            self.ctx.emit({"type": "workflow_node_start", "node": node_id})
            if self.ctx.trace:
                self.ctx.trace.emit("workflow_node_start", node_id, {"inputs": node_inputs})
            output = await block.run(self.ctx, node_inputs)
            result.node_outputs[node_id] = output
            self.ctx.emit({"type": "workflow_node_end", "node": node_id, "output": output})
            if self.ctx.trace:
                self.ctx.trace.emit("workflow_node_end", node_id, {"output": output})
            seen.add(node_id)
            order.append(node_id)
            routes = output.get("__route__")
            if routes:
                for route_id in routes:
                    if route_id in nodes:
                        ready.appendleft(route_id)
                continue
            for target_id, _, _ in outgoing.get(node_id, []):
                if is_ready(target_id):
                    ready.append(target_id)

        if order:
            result.outputs = result.node_outputs.get(order[-1], {})
        return result
