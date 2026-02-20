"""Factory to build actions from text."""

from __future__ import annotations

from rebot.actions.action import ActionNode
from rebot.models.base import ChatModel
from rebot.tools.base import SimpleTool
from rebot.tools.fs_tools import ListFilesTool, ReadFileTool, WriteFileTool


def build_action_from_text(text: str, model: ChatModel | None = None) -> ActionNode:
    return ActionNode(name=text[:32], prompt=text, model=model)


def build_tool_action(text: str, model: ChatModel | None = None) -> ActionNode:
    prompt = (
        "Map the action to tool steps. If tool is needed, output a tool call schema. "
        "Action: " + text
    )
    return ActionNode(name=f"tool_{text[:24]}", prompt=prompt, model=model)
