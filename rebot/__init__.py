"""Rebot SDK."""

from rebot.core.messages import Message, ToolCall
from rebot.core.runnable import (
    Runnable,
    RunnableLambda,
    RunnableSequence,
    RunnableParallel,
    RunnablePassthrough,
    RunnableConfigurable,
    RunnableContext,
    SimpleRunnableCallbacks,
    RunnableTrace,
)
from rebot.agents.agent import Agent
from rebot.tools.base import BaseTool
from rebot.agents.structured_output import AutoStrategy, ProviderStrategy, ToolStrategy
from rebot.models.openai_compatible import OpenAICompatibleChatModel
from rebot.models.anthropic import AnthropicChatModel
from rebot.models.config import ModelConfig
from rebot.models.providers import (
    MODEL_PROVIDERS,
    ModelProviderRegistry,
    create_chat_model,
    infer_provider_name,
    normalize_provider_alias,
)
from rebot.agents.coding_agent import CodingAgent
from rebot.agents.reporting import ReportMiddleware
from rebot.agents.review import ReviewMiddleware
from rebot.agents.planning import PlanningMiddleware
from rebot.agents.reasoning_chain import ReasoningChainMiddleware
from rebot.core.callbacks import CallbackManager, EventStreamHandler, create_event_manager
from rebot.core.trace import TraceCollector
from rebot.core.serialization import to_dict
from rebot.agents.graph_runtime import GraphRuntime, build_simple_agent_graph
from rebot.agents.dynamic_tools import DynamicToolMiddleware
from rebot.context import Context, CostManager
from rebot.team import Team
from rebot.environment.base import Environment
from rebot.environment.mgx import MGXEnvironment
from rebot.roles.role import Role
from rebot.roles.context import RoleContext
from rebot.actions.action import Action, SimpleAction, ActionNode, CompositeAction
from rebot.actions.action_factory import build_action_from_text
from rebot.auto.generate import OneShotGenerator, GeneratorConfig
from rebot.auto.metagpt_chain import MetaGPTChain
from rebot.roles.metagpt_pipeline import MetaGPTRolePipeline
from rebot.agents.autogpt_loop import AutoGPTLoop, Goal
from rebot.agents.context_compress import (
    COMPRESS_NONE,
    COMPRESS_RECENT_ONLY,
    COMPRESS_HEAD_TAIL,
    COMPRESS_SUMMARY_STUB,
    COMPRESS_STRATEGIES,
    normalize_compress_type,
)
from rebot.agents.vector_memory import VectorMemory
from rebot.agents.pgvector_memory import PgVectorMemory
from rebot.team_scheduler import TeamScheduler
from rebot.team_dag import TeamDAGScheduler, TaskDAG, TaskNode
from rebot.workflows import (
    WorkflowSpec,
    WorkflowResult,
    BlockSpec,
    EdgeSpec,
    INPUT_NODE,
    BlockRegistry,
    create_default_registry,
    WorkflowExecutor,
    ExecutionContext,
    LLMBlock,
    LLMBlockConfig,
    ToolBlock,
    ToolBlockConfig,
    RouterBlock,
    RouterBlockConfig,
    RouteOption,
)
from rebot.schema import RoutedMessage

__all__ = [
    "Agent",
    "AnthropicChatModel",
    "AutoStrategy",
    "BaseTool",
    "Message",
    "ModelConfig",
    "MODEL_PROVIDERS",
    "ModelProviderRegistry",
    "create_chat_model",
    "infer_provider_name",
    "normalize_provider_alias",
    "CodingAgent",
    "PlanningMiddleware",
    "ReportMiddleware",
    "ReviewMiddleware",
    "ReasoningChainMiddleware",
    "CallbackManager",
    "EventStreamHandler",
    "create_event_manager",
    "TraceCollector",
    "to_dict",
    "GraphRuntime",
    "build_simple_agent_graph",
    "DynamicToolMiddleware",
    "Context",
    "CostManager",
    "Team",
    "Environment",
    "MGXEnvironment",
    "Role",
    "RoleContext",
    "Action",
    "SimpleAction",
    "ActionNode",
    "CompositeAction",
    "build_action_from_text",
    "OneShotGenerator",
    "GeneratorConfig",
    "MetaGPTChain",
    "MetaGPTRolePipeline",
    "AutoGPTLoop",
    "Goal",
    "COMPRESS_NONE",
    "COMPRESS_RECENT_ONLY",
    "COMPRESS_HEAD_TAIL",
    "COMPRESS_SUMMARY_STUB",
    "COMPRESS_STRATEGIES",
    "normalize_compress_type",
    "VectorMemory",
    "PgVectorMemory",
    "TeamScheduler",
    "TeamDAGScheduler",
    "TaskDAG",
    "TaskNode",
    "RoutedMessage",
    "OpenAICompatibleChatModel",
    "ProviderStrategy",
    "Runnable",
    "RunnableLambda",
    "RunnableSequence",
    "RunnableParallel",
    "RunnablePassthrough",
    "RunnableConfigurable",
    "RunnableContext",
    "SimpleRunnableCallbacks",
    "RunnableTrace",
    "ToolCall",
    "ToolStrategy",
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
