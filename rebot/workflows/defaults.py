"""Default workflow registry."""

from __future__ import annotations

from rebot.workflows.registry import BlockRegistry
from rebot.workflows.blocks.llm import LLMBlock, LLMBlockConfig
from rebot.workflows.blocks.tool import ToolBlock, ToolBlockConfig
from rebot.workflows.blocks.router import RouterBlock, RouterBlockConfig


def create_default_registry() -> BlockRegistry:
    registry = BlockRegistry()
    registry.register("llm", lambda cfg: LLMBlock(LLMBlockConfig(**cfg)))
    registry.register("tool", lambda cfg: ToolBlock(ToolBlockConfig(**cfg)))
    registry.register("router", lambda cfg: RouterBlock(RouterBlockConfig(**cfg)))
    return registry
