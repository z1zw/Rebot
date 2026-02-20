"""MetaGPT-style PRD -> Design -> Tasks chain."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from pydantic import BaseModel, Field

from rebot.core.messages import Message
from rebot.models.base import ChatModel


class PRDSchema(BaseModel):
    product: str
    goals: list[str] = Field(default_factory=list)
    users: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class DesignSchema(BaseModel):
    architecture: list[str] = Field(default_factory=list)
    data_models: list[str] = Field(default_factory=list)
    api_endpoints: list[str] = Field(default_factory=list)
    ui_flow: list[str] = Field(default_factory=list)


class TaskSchema(BaseModel):
    tasks: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)


@dataclass
class MetaGPTChain:
    model: ChatModel

    def build_prd(self, requirement: str) -> PRDSchema:
        prompt = "Generate PRD JSON with product, goals, users, features, constraints."
        return _invoke(self.model, prompt, PRDSchema, requirement)

    def build_design(self, prd: PRDSchema) -> DesignSchema:
        prompt = "Generate Design JSON with architecture, data_models, api_endpoints, ui_flow."
        return _invoke(self.model, prompt, DesignSchema, prd.model_dump_json())

    def build_tasks(self, design: DesignSchema) -> TaskSchema:
        prompt = "Generate Task plan JSON with tasks and milestones."
        return _invoke(self.model, prompt, TaskSchema, design.model_dump_json())


def _invoke(model: ChatModel, prompt: str, schema: type[BaseModel], content: str):
    if getattr(model, "supports_response_format", False):
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
        }
        msg = model.invoke(
            [Message(role="user", content=f"{prompt}\n\n{content}")],
            tools=[],
            response_format=response_format,
        )
        return _parse_schema(model, prompt, content, schema, msg.content)
    msg = model.invoke(
        [Message(role="user", content=f"{prompt}\n\nReturn JSON only.\n\n{content}")],
        tools=[],
    )
    return _parse_schema(model, prompt, content, schema, msg.content)


def _parse_schema(model: ChatModel, prompt: str, content: str, schema: type[BaseModel], raw: str):
    def _try_parse(candidate: str):
        try:
            return schema.model_validate_json(candidate)
        except Exception:
            extracted = _extract_json_object(candidate)
            if extracted:
                try:
                    data = json.loads(extracted)
                    normalized = _normalize_payload(schema, data)
                    return schema.model_validate(normalized)
                except Exception:
                    return None
            return None

    parsed = _try_parse(raw)
    if parsed is not None:
        return parsed

    response_format = {
        "type": "json_schema",
        "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
    }
    candidate = raw
    for _ in range(3):
        repair_prompt = (
            f"{prompt}\n\n"
            "Return STRICT valid JSON only, no markdown fences, no comments.\n"
            "Close all strings and braces correctly.\n"
            f"Schema fields: {list(schema.model_fields.keys())}\n\n"
            f"Input context:\n{content}\n\n"
            f"Broken JSON candidate:\n{candidate}"
        )
        repaired = model.invoke(
            [Message(role="user", content=repair_prompt)],
            tools=[],
            response_format=response_format if getattr(model, "supports_response_format", False) else None,
        )
        candidate = repaired.content
        parsed = _try_parse(candidate)
        if parsed is not None:
            return parsed
    raise ValueError(f"{schema.__name__} JSON parsing failed after retries.")


def _normalize_payload(schema: type[BaseModel], payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)

    if schema is PRDSchema:
        normalized["product"] = _coerce_to_text(normalized.get("product", "Generated Product"))
        for key in ("goals", "users", "features", "constraints"):
            normalized[key] = _normalize_list(normalized.get(key, []))
        return normalized

    if schema is DesignSchema:
        for key in ("architecture", "data_models", "api_endpoints", "ui_flow"):
            normalized[key] = _normalize_list(normalized.get(key, []))
        return normalized

    if schema is TaskSchema:
        for key in ("tasks", "milestones"):
            normalized[key] = _normalize_list(normalized.get(key, []))
        return normalized

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
