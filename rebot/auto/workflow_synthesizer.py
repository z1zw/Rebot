"""Workflow synthesizer."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
from typing import Any

from pydantic import BaseModel, Field

from rebot.auto.spec_compiler import SpecSchema
from rebot.auto.task_planner import TaskPlanSchema
from rebot.core.messages import Message
from rebot.models.base import ChatModel
from rebot.workflows.schema import WorkflowSpec, BlockSpec, EdgeSpec, INPUT_NODE


class WorkflowSchema(BaseModel):
    workflow: WorkflowSpec
    notes: list[str] = Field(default_factory=list)
    perspective_tasks: list[str] = Field(default_factory=list)


@dataclass
class WorkflowSynthesizer:
    model: ChatModel

    def synthesize(
        self, spec: SpecSchema, plan: TaskPlanSchema, *, perspective_tasks: list[str] | None = None
    ) -> WorkflowSchema:
        prompt = (
            "Create a compact executable workflow with nodes and edges for the task plan. "
            "Keep it short. Use only fields required by WorkflowSchema. Return JSON only."
        )
        compact_tasks = [_extract_task_name(t) for t in (plan.tasks or [])]
        compact_tasks = [t for t in compact_tasks if t][:12]
        payload = {
            "product": spec.product,
            "platforms": spec.platforms,
            "tasks": compact_tasks,
            "perspective_tasks": (perspective_tasks or [])[:12],
        }
        if getattr(self.model, "supports_response_format", False):
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "WorkflowSchema",
                    "schema": WorkflowSchema.model_json_schema(),
                },
            }
            msg = self.model.invoke(
                [Message(role="user", content=f"{prompt}\n\n{payload}")],
                tools=[],
                response_format=response_format,
            )
            data = self._parse_or_repair(msg.content, prompt, payload)
            data = _normalize_workflow_schema(data, payload)
            return _ensure_perspective_tasks(data, perspective_tasks or [])
        msg = self.model.invoke(
            [Message(role="user", content=f"{prompt}\n\nReturn JSON only.\n\n{payload}")],
            tools=[],
        )
        data = self._parse_or_repair(msg.content, prompt, payload)
        data = _normalize_workflow_schema(data, payload)
        return _ensure_perspective_tasks(data, perspective_tasks or [])

    def _parse_or_repair(self, raw: str, prompt: str, payload: dict[str, Any]) -> WorkflowSchema:
        attempts: list[dict[str, Any]] = []

        def _try_parse(candidate: str) -> WorkflowSchema | None:
            try:
                return WorkflowSchema.model_validate_json(candidate)
            except Exception:
                extracted = _extract_json_object(candidate)
                if extracted:
                    try:
                        return WorkflowSchema.model_validate_json(extracted)
                    except Exception:
                        return None
                return None

        attempts.append({"stage": "initial", "content": raw})
        parsed = _try_parse(raw)
        if parsed is not None:
            return parsed

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "WorkflowSchema",
                "schema": WorkflowSchema.model_json_schema(),
            },
        }

        candidate = raw
        for i in range(3):
            clipped = candidate[-6000:] if candidate else ""
            repair_prompt = (
                f"{prompt}\n\n"
                "Return STRICT valid JSON only, no markdown fences, no comments.\n"
                "Close all strings and braces correctly.\n"
                f"Schema fields: {list(WorkflowSchema.model_fields.keys())}\n\n"
                f"Input context:\n{payload}\n\n"
                f"Broken JSON candidate:\n{clipped}"
            )
            repaired = self.model.invoke(
                [Message(role="user", content=repair_prompt)],
                tools=[],
                response_format=response_format if getattr(self.model, "supports_response_format", False) else None,
            )
            candidate = repaired.content
            attempts.append({"stage": f"repair_{i + 1}", "content": candidate})
            parsed = _try_parse(candidate)
            if parsed is not None:
                return parsed

        dump_path = _dump_workflow_debug(payload=payload, attempts=attempts)
        snippet = (candidate or "")[:400].replace("\n", "\\n")
        # Hard fallback: build a deterministic executable workflow from plan tasks.
        return _fallback_workflow_schema(payload, notes=[
            f"workflow_parse_failed_debug={dump_path}",
            f"workflow_last_snippet={snippet}",
        ])


def _ensure_perspective_tasks(schema: WorkflowSchema, tasks: list[str]) -> WorkflowSchema:
    if not tasks:
        return schema
    workflow = schema.workflow
    nodes = list(workflow.nodes)
    edges = list(workflow.edges)
    start_id = workflow.entrypoint or (nodes[0].id if nodes else "start")
    for idx, task in enumerate(tasks):
        node_id = f"perspective_{idx}"
        nodes.append(
            BlockSpec(id=node_id, type="llm", config={"prompt": f"Execute: {task}"})
        )
        edges.append(
            EdgeSpec(
                source=INPUT_NODE,
                source_key="requirement",
                target=node_id,
                target_key="task",
            )
        )
    if not workflow.entrypoint and nodes:
        workflow.entrypoint = nodes[0].id
    workflow.nodes = nodes
    workflow.edges = edges
    return WorkflowSchema(workflow=workflow, notes=schema.notes, perspective_tasks=tasks)


def _normalize_workflow_schema(schema: WorkflowSchema, payload: dict[str, Any]) -> WorkflowSchema:
    nodes: list[BlockSpec] = []
    edges: list[EdgeSpec] = []
    for node in schema.workflow.nodes:
        node_type = (node.type or "llm").strip().lower()
        if node_type not in {"llm", "tool", "router"}:
            node_type = "llm"
        config = dict(node.config or {})
        if node_type == "llm" and "prompt" not in config:
            config["prompt"] = (
                f"Task node '{node.id}'. Use requirement: {{requirement}}. "
                "Continue based on available previous outputs."
            )
        nodes.append(BlockSpec(id=node.id, type=node_type, config=config))
    for edge in schema.workflow.edges:
        source_key = edge.source_key or "text"
        target_key = edge.target_key or "input"
        edges.append(
            EdgeSpec(
                source=edge.source,
                source_key=source_key,
                target=edge.target,
                target_key=target_key,
            )
        )
    for node in nodes:
        has_requirement = any(
            e.source == INPUT_NODE and e.target == node.id and e.target_key == "requirement"
            for e in edges
        )
        if not has_requirement:
            edges.append(
                EdgeSpec(
                    source=INPUT_NODE,
                    source_key="requirement",
                    target=node.id,
                    target_key="requirement",
                )
            )
    normalized = WorkflowSchema(
        workflow=WorkflowSpec(
            nodes=nodes,
            edges=edges,
            entrypoint=schema.workflow.entrypoint or (nodes[0].id if nodes else None),
        ),
        notes=list(schema.notes),
        perspective_tasks=list(schema.perspective_tasks),
    )
    if not normalized.workflow.nodes:
        return _fallback_workflow_schema(payload, notes=normalized.notes + ["workflow_empty_after_normalize"])
    return normalized


def _fallback_workflow_schema(payload: dict[str, Any], notes: list[str] | None = None) -> WorkflowSchema:
    raw_tasks: list[Any] = []
    if isinstance(payload, dict):
        tasks = payload.get("tasks")
        if isinstance(tasks, list):
            raw_tasks = tasks
        else:
            plan = payload.get("plan")
            if isinstance(plan, dict) and isinstance(plan.get("tasks"), list):
                raw_tasks = plan.get("tasks") or []
    task_names = [_extract_task_name(t) for t in raw_tasks]
    task_names = [t for t in task_names if t]
    if not task_names:
        task_names = ["Implement core feature", "Build UI", "Run basic validation"]
    nodes: list[BlockSpec] = []
    edges: list[EdgeSpec] = []
    prev_node_id: str | None = None
    for idx, task in enumerate(task_names):
        node_id = f"task_{idx + 1}"
        nodes.append(
            BlockSpec(
                id=node_id,
                type="llm",
                config={
                    "prompt": (
                        f"Execute this task step-by-step: {task}. "
                        "Use requirement: {requirement}. "
                        "If prior output exists, continue from it."
                    )
                },
            )
        )
        edges.append(
            EdgeSpec(
                source=INPUT_NODE,
                source_key="requirement",
                target=node_id,
                target_key="requirement",
            )
        )
        if prev_node_id is not None:
            edges.append(
                EdgeSpec(
                    source=prev_node_id,
                    source_key="text",
                    target=node_id,
                    target_key="input",
                )
            )
        prev_node_id = node_id
    return WorkflowSchema(
        workflow=WorkflowSpec(nodes=nodes, edges=edges, entrypoint=nodes[0].id if nodes else None),
        notes=(notes or []) + ["workflow_fallback_generated=true"],
        perspective_tasks=[],
    )


def _extract_task_name(task: Any) -> str:
    if isinstance(task, dict):
        if "task" in task:
            return str(task["task"]).strip()
        return str(task).strip()
    if not isinstance(task, str):
        return str(task).strip()
    s = task.strip()
    if not s:
        return ""
    if s.startswith("{") and s.endswith("}"):
        try:
            data = json.loads(s)
            if isinstance(data, dict) and "task" in data:
                return str(data["task"]).strip()
        except Exception:
            return s
    return s


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return None


def _dump_workflow_debug(*, payload: dict[str, Any], attempts: list[dict[str, Any]]) -> str:
    root = Path(tempfile.gettempdir()) / "rebot_workflow_debug"
    root.mkdir(parents=True, exist_ok=True)
    idx = len(list(root.glob("workflow_debug_*.json"))) + 1
    path = root / f"workflow_debug_{idx}.json"
    path.write_text(
        json.dumps({"payload": payload, "attempts": attempts}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)
