"""Workflow schema definitions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


INPUT_NODE = "__input__"


class BlockSpec(BaseModel):
    id: str
    type: str
    config: dict[str, Any] = Field(default_factory=dict)


class EdgeSpec(BaseModel):
    source: str
    source_key: str
    target: str
    target_key: str


class WorkflowSpec(BaseModel):
    nodes: list[BlockSpec] = Field(default_factory=list)
    edges: list[EdgeSpec] = Field(default_factory=list)
    entrypoint: str | None = None


class WorkflowResult(BaseModel):
    outputs: dict[str, Any] = Field(default_factory=dict)
    node_outputs: dict[str, dict[str, Any]] = Field(default_factory=dict)
