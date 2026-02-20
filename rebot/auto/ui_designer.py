"""Automatic UI designer for iOS (SwiftUI)."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from pydantic import BaseModel, Field

from rebot.auto.spec_compiler import SpecSchema
from rebot.core.messages import Message
from rebot.models.base import ChatModel
from rebot.auto.templates.ui_templates import TEMPLATES


class UIDesignSchema(BaseModel):
    theme_name: str
    colors: dict[str, str] = Field(default_factory=dict)
    typography: dict[str, str] = Field(default_factory=dict)
    spacing: dict[str, int] = Field(default_factory=dict)
    radius: dict[str, int] = Field(default_factory=dict)
    pages: list[str] = Field(default_factory=list)


@dataclass
class UIDesigner:
    model: ChatModel

    def design(self, spec: SpecSchema, platform: str) -> UIDesignSchema:
        prompt = (
            "Design a high-quality UI theme and page list for the given product. "
            "Return JSON with colors, typography, spacing, radius, pages."
        )
        category = _infer_category(spec)
        template = TEMPLATES.get(category, TEMPLATES["tools"])
        content = spec.model_dump_json()
        if getattr(self.model, "supports_response_format", False):
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "UIDesignSchema",
                    "schema": UIDesignSchema.model_json_schema(),
                },
            }
            msg = self.model.invoke(
                [
                    Message(
                        role="user",
                        content=(
                            f"{prompt}\n\nPlatform: {platform}\n\n"
                            f"Category: {category}\nTemplate: {template}\n\n{content}"
                        ),
                    )
                ],
                tools=[],
                response_format=response_format,
            )
            return _parse_schema_with_repair(self.model, UIDesignSchema, msg.content, prompt, content, platform, category, template)
        msg = self.model.invoke(
            [
                Message(
                    role="user",
                    content=(
                        f"{prompt}\n\nReturn JSON only.\n\nPlatform: {platform}\n\n"
                        f"Category: {category}\nTemplate: {template}\n\n{content}"
                    ),
                )
            ],
            tools=[],
        )
        return _parse_schema_with_repair(self.model, UIDesignSchema, msg.content, prompt, content, platform, category, template)


def _infer_category(spec: SpecSchema) -> str:
    text = " ".join(spec.features + spec.goals + [spec.product]).lower()
    if any(k in text for k in ["fitness", "workout", "exercise", "sport", "training"]):
        return "fitness"
    if any(k in text for k in ["health", "wellness", "sleep", "nutrition", "habit"]):
        return "health"
    if any(k in text for k in ["shop", "cart", "product", "ecommerce"]):
        return "ecommerce"
    if any(k in text for k in ["finance", "budget", "bank", "wallet", "investment"]):
        return "finance"
    if any(k in text for k in ["course", "lesson", "study", "learn", "education"]):
        return "education"
    if any(k in text for k in ["travel", "trip", "flight", "hotel", "itinerary"]):
        return "travel"
    if any(k in text for k in ["music", "video", "podcast", "media", "stream"]):
        return "media"
    if any(k in text for k in ["enterprise", "b2b", "workflow", "analytics", "dashboard"]):
        return "enterprise"
    if any(k in text for k in ["social", "feed", "chat", "friends"]):
        return "social"
    return "tools"


def _parse_schema_with_repair(
    model: ChatModel,
    schema: type[BaseModel],
    raw: str,
    prompt: str,
    content: str,
    platform: str,
    category: str,
    template: dict[str, Any],
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
            data = _normalize_ui_payload(data)
            return schema.model_validate(data)
        except Exception:
            pass
    for _ in range(retries):
        repair_prompt = (
            f"{prompt}\n\n"
            "Return valid JSON only. No markdown, no explanation, no trailing text.\n"
            f"Target schema: {schema.model_json_schema()}\n\n"
            "If previous JSON is truncated or has wrong field types, repair it to match schema exactly.\n\n"
            f"Platform: {platform}\nCategory: {category}\nTemplate: {template}\n\n"
            f"Spec:\n{content}\n\n"
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
                    data = _normalize_ui_payload(data)
                    return schema.model_validate(data)
                except Exception:
                    continue
    raise ValueError("UI design JSON parse failed after repair retries")


def _normalize_ui_payload(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {
            "theme_name": "Default",
            "colors": {},
            "typography": {},
            "spacing": {},
            "radius": {},
            "pages": [],
        }
    out = dict(data)
    out["theme_name"] = str(out.get("theme_name") or "Default")
    out["colors"] = _normalize_dict_str(out.get("colors"))
    out["typography"] = _normalize_dict_str(out.get("typography"))
    out["spacing"] = _normalize_dict_int(out.get("spacing"))
    out["radius"] = _normalize_dict_int(out.get("radius"))
    out["pages"] = _normalize_str_list(out.get("pages"))
    return out


def _normalize_dict_str(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    return {}


def _normalize_dict_int(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, int] = {}
    for k, v in value.items():
        try:
            out[str(k)] = int(v)
        except Exception:
            continue
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
