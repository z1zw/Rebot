"""Workflow engine."""

from rebot.workflows.schema import WorkflowSpec, WorkflowResult, BlockSpec, EdgeSpec, INPUT_NODE
from rebot.workflows.registry import BlockRegistry
from rebot.workflows.defaults import create_default_registry
from rebot.workflows.executor import WorkflowExecutor
from rebot.workflows.blocks.base import ExecutionContext
from rebot.workflows.blocks.llm import LLMBlock, LLMBlockConfig
from rebot.workflows.blocks.tool import ToolBlock, ToolBlockConfig
from rebot.workflows.blocks.router import RouterBlock, RouterBlockConfig, RouteOption

__all__ = [
    "WorkflowSpec",
    "WorkflowResult",
    "BlockSpec",
    "EdgeSpec",
    "INPUT_NODE",
    "BlockRegistry",
    "create_default_registry",
    "WorkflowExecutor",
    "ExecutionContext",
    "LLMBlock",
    "LLMBlockConfig",
    "ToolBlock",
    "ToolBlockConfig",
    "RouterBlock",
    "RouterBlockConfig",
    "RouteOption",
]
