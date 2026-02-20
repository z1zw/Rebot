"""Spec compiler for one-line requirements."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from pydantic import BaseModel, Field

from rebot.core.messages import Message
from rebot.models.base import ChatModel


class SpecSchema(BaseModel):
    product: str
    goals: list[str] = Field(default_factory=list)
    users: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    non_functional: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


@dataclass
class SpecCompiler:
    model: ChatModel

    def compile(self, text: str, *, language: str, platforms: list[str]) -> SpecSchema:
        prompt = (
            "Turn the requirement into a product spec JSON. "
            "Include goals, users, platforms, features, non_functional, constraints, risks."
        )
        content = f"Requirement: {text}\nLanguage: {language}\nPlatforms: {platforms}"
        if getattr(self.model, "supports_response_format", False):
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "SpecSchema",
                    "schema": SpecSchema.model_json_schema(),
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

    def _parse_or_repair(self, raw: str, prompt: str, content: str) -> SpecSchema:
        def _try_parse(candidate: str) -> SpecSchema | None:
            try:
                return _validate_spec_json(candidate)
            except Exception:
                extracted = _extract_json_object(candidate)
                if extracted:
                    try:
                        return _validate_spec_json(extracted)
                    except Exception:
                        return None
                return None

        parsed = _try_parse(raw)
        if parsed is not None:
            return parsed

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "SpecSchema",
                "schema": SpecSchema.model_json_schema(),
            },
        }
        candidate = raw
        for _ in range(3):
            repair_prompt = (
                f"{prompt}\n\n"
                "Return STRICT valid JSON only, no markdown fences, no comments.\n"
                "Close all strings and braces correctly.\n"
                f"Schema fields: {list(SpecSchema.model_fields.keys())}\n\n"
                f"Original requirement context:\n{content}\n\n"
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
        raise ValueError("Spec JSON parsing failed after retries.")


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


def _validate_spec_json(raw: str) -> SpecSchema:
    payload = json.loads(raw)
    normalized = _normalize_spec_payload(payload)
    return SpecSchema.model_validate(normalized)


def _normalize_spec_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    for key in ("goals", "users", "platforms", "features", "non_functional", "constraints", "risks"):
        value = normalized.get(key, [])
        if not isinstance(value, list):
            value = [value]
        normalized[key] = [_coerce_to_text(item) for item in value if item is not None]
    normalized["product"] = _coerce_to_text(normalized.get("product", "Generated Product"))
    return normalized


def _coerce_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        # Convert {"name": "...", "description": "..."} style objects into a readable line.
        parts: list[str] = []
        for k, v in value.items():
            if v is None:
                continue
            parts.append(f"{k}: {_coerce_to_text(v)}")
        return " | ".join(parts) if parts else json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return ", ".join(_coerce_to_text(v) for v in value)
    return str(value)
