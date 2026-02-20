"""Structured output strategies."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Generic, TypeVar

from pydantic import TypeAdapter
from rebot.tools.structured import StructuredOutputTool

SchemaT = TypeVar("SchemaT")


@dataclass(frozen=True)
class ToolStrategy(Generic[SchemaT]):
    schema: type[SchemaT] | dict[str, Any]
    tool_name: str | None = None
    handle_errors: bool = True
    tool_message_content: str | None = None


@dataclass(frozen=True)
class ProviderStrategy(Generic[SchemaT]):
    schema: type[SchemaT] | dict[str, Any]
    strict: bool | None = None


@dataclass(frozen=True)
class AutoStrategy(Generic[SchemaT]):
    schema: type[SchemaT] | dict[str, Any]


ResponseFormat = ToolStrategy[SchemaT] | ProviderStrategy[SchemaT] | AutoStrategy[SchemaT]


def schema_name(schema: type[Any] | dict[str, Any]) -> str:
    if isinstance(schema, dict):
        return str(schema.get("title") or "structured_output")
    return getattr(schema, "__name__", "structured_output")


def parse_structured(schema: type[Any] | dict[str, Any], data: Any) -> Any:
    if isinstance(schema, dict):
        return data
    adapter = TypeAdapter(schema)
    return adapter.validate_python(data)


def parse_json_message(content: str) -> Any:
    return json.loads(content)


def resolve_response_format(
    response_format: ResponseFormat | None, *, supports_provider: bool
) -> ResponseFormat | None:
    if isinstance(response_format, AutoStrategy):
        if supports_provider:
            return ProviderStrategy(schema=response_format.schema)
        return ToolStrategy(schema=response_format.schema)
    return response_format


def provider_kwargs(response_format: ResponseFormat | None) -> dict[str, object] | None:
    if isinstance(response_format, ProviderStrategy):
        schema = response_format.schema
        name = schema_name(schema)
        json_schema = schema if isinstance(schema, dict) else TypeAdapter(schema).json_schema()
        payload = {"name": name, "schema": json_schema}
        if response_format.strict:
            payload["strict"] = True
        return {"type": "json_schema", "json_schema": payload}
    return None


def structured_tool_from_strategy(strategy: ToolStrategy) -> StructuredOutputTool:
    name = strategy.tool_name or schema_name(strategy.schema)
    json_schema = (
        strategy.schema
        if isinstance(strategy.schema, dict)
        else TypeAdapter(strategy.schema).json_schema()
    )
    return StructuredOutputTool(
        name=name,
        description="Structured output tool",
        input_schema=json_schema,
    )


def parse_structured_from_message(
    response_format: ResponseFormat | None, message: Any
) -> tuple[bool, Any | None, str | None]:
    if response_format is None:
        return False, None, None
    if isinstance(response_format, ProviderStrategy):
        try:
            data = parse_json_message(message.content)
            return True, parse_structured(response_format.schema, data), None
        except Exception as exc:  # noqa: BLE001
            return False, None, str(exc)
    if isinstance(response_format, ToolStrategy):
        tool_name = response_format.tool_name or schema_name(response_format.schema)
        for tc in message.tool_calls:
            if tc.name == tool_name:
                try:
                    return True, parse_structured(response_format.schema, tc.args), None
                except Exception as exc:  # noqa: BLE001
                    return False, None, str(exc)
    return False, None, None
