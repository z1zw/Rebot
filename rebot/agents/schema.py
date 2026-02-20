"""State schema merge helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, get_type_hints, Annotated


@dataclass(frozen=True)
class OmitFromSchema:
    input: bool = True
    output: bool = True


def _extract_metadata(type_: Any) -> list[Any]:
    origin = getattr(type_, "__origin__", None)
    if origin is Annotated:
        return list(getattr(type_, "__metadata__", []))
    return []


def merge_state_schema(schemas: set[type], omit_flag: str | None = None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for schema in schemas:
        hints = get_type_hints(schema, include_extras=True)
        for name, t in hints.items():
            if omit_flag:
                metadata = _extract_metadata(t)
                if any(
                    isinstance(m, OmitFromSchema) and getattr(m, omit_flag) is True
                    for m in metadata
                ):
                    continue
            merged[name] = t
    return merged
