"""Tool execution block."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from rebot.workflows.blocks.base import Block, ExecutionContext


class ToolBlockConfig(BaseModel):
    tool: str
    return_key: str = "result"


@dataclass
class ToolBlock(Block):
    config: ToolBlockConfig

    async def run(self, ctx: ExecutionContext, inputs: dict[str, Any]) -> dict[str, Any]:
        tool = ctx.tools.get(self.config.tool)
        if tool is None:
            raise RuntimeError(f"Tool '{self.config.tool}' not found.")
        result = await asyncio.to_thread(tool.run, inputs)
        return {self.config.return_key: result}
