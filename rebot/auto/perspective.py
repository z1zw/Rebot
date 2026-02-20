"""Perspective expansion and injection."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from pydantic import BaseModel, Field

from rebot.core.messages import Message
from rebot.models.base import ChatModel


class PerspectiveSchema(BaseModel):
    missing_views: list[str] = Field(default_factory=list)
    injected_rules: list[str] = Field(default_factory=list)
    priority: list[str] = Field(default_factory=list)


@dataclass
class PerspectiveExpander:
    model: ChatModel

    def expand(self, spec: dict[str, Any], arch: dict[str, Any]) -> PerspectiveSchema:
        prompt = (
            "Identify missing perspectives for the project (e.g., security, UI, data integrity, "
            "performance, compliance). Return JSON with missing_views, injected_rules, priority."
        )
        payload = {"spec": spec, "arch": arch}
        if getattr(self.model, "supports_response_format", False):
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "PerspectiveSchema",
                    "schema": PerspectiveSchema.model_json_schema(),
                },
            }
            msg = self.model.invoke(
                [Message(role="user", content=f"{prompt}\n\n{payload}")],
                tools=[],
                response_format=response_format,
            )
            return _parse_schema_with_repair(self.model, PerspectiveSchema, msg.content, prompt, str(payload))
        msg = self.model.invoke(
            [Message(role="user", content=f"{prompt}\n\nReturn JSON only.\n\n{payload}")],
            tools=[],
        )
        return _parse_schema_with_repair(self.model, PerspectiveSchema, msg.content, prompt, str(payload))


def _parse_schema_with_repair(
    model: ChatModel,
    schema: type[BaseModel],
    raw: str,
    prompt: str,
    payload: str,
    retries: int = 3,
) -> BaseModel:
    try:
        return schema.model_validate_json(raw)
    except Exception:
        pass
    extracted = _extract_json_object(raw)
    if extracted:
        try:
            data = json.loads(extracted)
            data = _normalize_perspective_payload(data)
            return schema.model_validate(data)
        except Exception:
            pass
    for _ in range(retries):
        repair_prompt = (
            f"{prompt}\n\n"
            "Return valid JSON only. No markdown, no explanation, no trailing text.\n"
            f"Target schema: {schema.model_json_schema()}\n\n"
            "If previous JSON is truncated or has wrong field types, repair it to match schema exactly.\n\n"
            f"Context:\n{payload}\n\n"
            f"Previous output:\n{raw}"
        )
        kwargs: dict[str, Any] = {"tools": []}
        if getattr(model, "supports_response_format", False):
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
            }
        msg = model.invoke([Message(role="user", content=repair_prompt)], **kwargs)
        raw = msg.content
        try:
            return schema.model_validate_json(raw)
        except Exception:
            extracted = _extract_json_object(raw)
            if extracted:
                try:
                    data = json.loads(extracted)
                    data = _normalize_perspective_payload(data)
                    return schema.model_validate(data)
                except Exception:
                    continue
    raise ValueError("Perspective JSON parse failed after repair retries")


def _normalize_perspective_payload(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"missing_views": [], "injected_rules": [], "priority": []}
    out = dict(data)
    for key in ["missing_views", "injected_rules", "priority"]:
        out[key] = _normalize_str_list(out.get(key))
    return out


def _normalize_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
            elif isinstance(item, dict):
                text = ", ".join(f"{k}: {v}" for k, v in item.items())
            else:
                text = str(item).strip()
            if text:
                out.append(text)
        return out
    if isinstance(value, dict):
        return [f"{k}: {v}" for k, v in value.items()]
    text = str(value).strip()
    return [text] if text else []


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None
