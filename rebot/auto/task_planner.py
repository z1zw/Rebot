"""Task planner for software generation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from pydantic import BaseModel, Field

from rebot.auto.spec_compiler import SpecSchema
from rebot.core.messages import Message
from rebot.models.base import ChatModel


class TaskPlanSchema(BaseModel):
    tasks: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)


@dataclass
class TaskPlanner:
    model: ChatModel

    def plan(self, spec: SpecSchema) -> TaskPlanSchema:
        prompt = "Generate a task plan for implementing the product. Return JSON."
        content = spec.model_dump_json()
        if getattr(self.model, "supports_response_format", False):
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "TaskPlanSchema",
                    "schema": TaskPlanSchema.model_json_schema(),
                },
            }
            msg = self.model.invoke(
                [Message(role="user", content=f"{prompt}\n\n{content}")],
                tools=[],
                response_format=response_format,
            )
            return self._parse_or_repair(msg.content, prompt, content)
        msg = self.model.invoke(
            [Message(role="user", content=f"{prompt}\n\nReturn JSON only.\n\n{content}")],
            tools=[],
        )
        return self._parse_or_repair(msg.content, prompt, content)

    def _parse_or_repair(self, raw: str, prompt: str, content: str) -> TaskPlanSchema:
        def _try_parse(candidate: str) -> TaskPlanSchema | None:
            try:
                return _validate_task_plan_json(candidate)
            except Exception:
                extracted = _extract_json_object(candidate)
                if extracted:
                    try:
                        return _validate_task_plan_json(extracted)
                    except Exception:
                        return None
                return None

        parsed = _try_parse(raw)
        if parsed is not None:
            return parsed

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "TaskPlanSchema",
                "schema": TaskPlanSchema.model_json_schema(),
            },
        }
        candidate = raw
        for _ in range(3):
            repair_prompt = (
                f"{prompt}\n\n"
                "Return STRICT valid JSON only, no markdown fences, no comments.\n"
                "Close all strings and braces correctly.\n"
                f"Schema fields: {list(TaskPlanSchema.model_fields.keys())}\n\n"
                f"Input context:\n{content}\n\n"
                f"Broken JSON candidate:\n{candidate}"
            )
            repaired = self.model.invoke(
                [Message(role="user", content=repair_prompt)],
                tools=[],
                response_format=response_format if getattr(self.model, "supports_response_format", False) else None,
            )
            candidate = repaired.content
            parsed = _try_parse(candidate)
            if parsed is not None:
                return parsed
        raise ValueError("Task plan JSON parsing failed after retries.")


def _validate_task_plan_json(raw: str) -> TaskPlanSchema:
    payload = json.loads(raw)
    normalized = _normalize_task_plan_payload(payload)
    return TaskPlanSchema.model_validate(normalized)


def _normalize_task_plan_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["tasks"] = _normalize_list(normalized.get("tasks", []))
    normalized["milestones"] = _normalize_list(normalized.get("milestones", []))
    return normalized


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_coerce_to_text(v) for v in value if v is not None]
    if isinstance(value, dict):
        return [_coerce_to_text(v) for v in value.values() if v is not None] or [
            _coerce_to_text(value)
        ]
    return [_coerce_to_text(value)]


def _coerce_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        parts: list[str] = []
        for k, v in value.items():
            if v is None:
                continue
            parts.append(f"{k}: {_coerce_to_text(v)}")
        return " | ".join(parts) if parts else json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return ", ".join(_coerce_to_text(v) for v in value)
    return str(value)


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
