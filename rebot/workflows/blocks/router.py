"""Routing block to choose next nodes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from rebot.core.messages import Message
from rebot.workflows.blocks.base import Block, ExecutionContext


class RouteOption(BaseModel):
    id: str
    description: str


class RouterBlockConfig(BaseModel):
    prompt: str
    options: list[RouteOption] = Field(default_factory=list)


@dataclass
class RouterBlock(Block):
    config: RouterBlockConfig

    async def run(self, ctx: ExecutionContext, inputs: dict[str, Any]) -> dict[str, Any]:
        model = ctx.model
        if model is None:
            raise RuntimeError("RouterBlock requires a model in ExecutionContext.")
        options = "\n".join(f"- {opt.id}: {opt.description}" for opt in self.config.options)
        prompt = self.config.prompt.format(**inputs)
        msg = await model.ainvoke(
            [
                Message(
                    role="user",
                    content=f"{prompt}\n\nChoose one option id from:\n{options}\n\nReturn the id only.",
                )
            ],
            tools=[],
        )
        route_id = msg.content.strip().splitlines()[0]
        return {"route": route_id, "__route__": [route_id]}
