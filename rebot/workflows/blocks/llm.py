"""LLM-based workflow blocks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from rebot.core.messages import Message
from rebot.workflows.blocks.base import Block, ExecutionContext


class LLMBlockConfig(BaseModel):
    prompt: str
    system: str | None = None
    response_schema: dict[str, Any] | None = None


@dataclass
class LLMBlock(Block):
    config: LLMBlockConfig

    async def run(self, ctx: ExecutionContext, inputs: dict[str, Any]) -> dict[str, Any]:
        model = ctx.model
        if model is None:
            raise RuntimeError("LLMBlock requires a model in ExecutionContext.")
        prompt = self.config.prompt.format(**inputs)
        messages = []
        if self.config.system:
            messages.append(Message(role="system", content=self.config.system))
        messages.append(Message(role="user", content=prompt))
        kwargs: dict[str, Any] = {}
        if self.config.response_schema and getattr(model, "supports_response_format", False):
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "WorkflowResponse",
                    "schema": self.config.response_schema,
                },
            }
        msg = await model.ainvoke(messages, tools=[], **kwargs)
        return {"text": msg.content}
