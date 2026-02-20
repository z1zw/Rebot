from __future__ import annotations

from typing import Any

from app.core.settings import settings


def list_llm_providers() -> list[dict[str, Any]]:
    return [
        {
            "id": "openai",
            "name": "OpenAI Compatible",
            "enabled": True,
            "supports_stream": True,
            "supports_reasoning": True,
            "default_base_url": "https://api.openai.com/v1",
            "models": ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"],
        },
        {
            "id": "anthropic",
            "name": "Anthropic Compatible",
            "enabled": True,
            "supports_stream": True,
            "supports_reasoning": True,
            "default_base_url": "https://api.anthropic.com/v1",
            "models": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
        },
        {
            "id": "deepseek",
            "name": "DeepSeek",
            "enabled": True,
            "supports_stream": True,
            "supports_reasoning": True,
            "default_base_url": "https://api.deepseek.com/v1",
            "models": ["deepseek-chat", "deepseek-reasoner"],
        },
        {
            "id": "ollama",
            "name": "Ollama (Local)",
            "enabled": True,
            "supports_stream": True,
            "supports_reasoning": False,
            "default_base_url": "http://localhost:11434/v1",
            "models": ["qwen2.5-coder", "llama3.1", "deepseek-coder-v2"],
        },
    ]


def list_tool_capabilities() -> list[dict[str, Any]]:
    return [
        {
            "id": "fs.list",
            "name": "List Files",
            "category": "filesystem",
            "enabled": True,
            "description": "Enumerate project files with depth limits.",
        },
        {
            "id": "fs.read",
            "name": "Read File",
            "category": "filesystem",
            "enabled": True,
            "description": "Read file content in workspace scope.",
        },
        {
            "id": "fs.write",
            "name": "Write File",
            "category": "filesystem",
            "enabled": True,
            "description": "Create or overwrite files in workspace scope.",
        },
        {
            "id": "fs.patch",
            "name": "Apply Patch",
            "category": "filesystem",
            "enabled": True,
            "description": "Structured patch editing with hunk-level safety.",
        },
        {
            "id": "cmd.run_tests",
            "name": "Run Tests",
            "category": "command",
            "enabled": True,
            "description": "Execute test commands inside validated sandbox.",
        },
        {
            "id": "git.clone",
            "name": "Git Clone",
            "category": "vcs",
            "enabled": True,
            "description": "Clone repositories and initialize workspace metadata.",
        },
        {
            "id": "intel.ast_index",
            "name": "AST Index",
            "category": "intelligence",
            "enabled": True,
            "description": "Build code structure index for scheduling and navigation.",
        },
        {
            "id": "orchestration.multi_agent",
            "name": "Multi-Agent Scheduler",
            "category": "orchestration",
            "enabled": True,
            "description": "Plan and execute parallel agent workflows with retries.",
        },
    ]


def resource_policy() -> dict[str, Any]:
    return {
        "max_model_concurrency": max(1, settings.model_max_concurrency_default),
        "max_split_concurrency": max(1, settings.split_max_concurrency_default),
        "task_queue_mode": "local" if settings.force_local_tasks or not settings.rabbitmq_url else "rabbitmq",
        "embed_worker": bool(settings.embed_worker),
        "observability": {
            "metrics_enabled": True,
            "tracing_enabled": bool(settings.tracing_enabled),
        },
    }
