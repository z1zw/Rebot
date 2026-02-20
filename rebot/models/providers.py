"""Provider registry and model factory."""

from __future__ import annotations

from typing import Callable

from rebot.models.anthropic import AnthropicChatModel
from rebot.models.base import ChatModel
from rebot.models.config import ModelConfig
from rebot.models.metagpt_alias import (
    BedrockChatModel,
    DashScopeChatModel,
    DeepSeekChatModel,
    GeminiChatModel,
    MoonshotChatModel,
    OpenRouterChatModel,
    QianfanChatModel,
)
from rebot.models.openai_compatible import OpenAICompatibleChatModel

ProviderFactory = Callable[[ModelConfig], ChatModel]


class ModelProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ProviderFactory] = {}

    def register(self, name: str, factory: ProviderFactory) -> None:
        self._providers[name.lower()] = factory

    def get(self, name: str) -> ProviderFactory:
        key = name.lower()
        if key not in self._providers:
            available = ", ".join(sorted(self._providers.keys()))
            raise ValueError(f"Unknown model provider '{name}'. Available: {available}")
        return self._providers[key]

    def create(self, name: str, config: ModelConfig) -> ChatModel:
        return self.get(name)(config)

    @property
    def names(self) -> list[str]:
        return sorted(self._providers.keys())


MODEL_PROVIDERS = ModelProviderRegistry()
MODEL_PROVIDERS.register("openai", lambda c: OpenAICompatibleChatModel(c))
MODEL_PROVIDERS.register("openai_compatible", lambda c: OpenAICompatibleChatModel(c))
MODEL_PROVIDERS.register("anthropic", lambda c: AnthropicChatModel(c))
MODEL_PROVIDERS.register("claude", lambda c: AnthropicChatModel(c))
# MetaGPT-style provider aliases routed to existing adapters.
MODEL_PROVIDERS.register("fireworks", lambda c: OpenAICompatibleChatModel(c))
MODEL_PROVIDERS.register("open_llm", lambda c: OpenAICompatibleChatModel(c))
MODEL_PROVIDERS.register("moonshot", lambda c: MoonshotChatModel(c))
MODEL_PROVIDERS.register("mistral", lambda c: OpenAICompatibleChatModel(c))
MODEL_PROVIDERS.register("yi", lambda c: OpenAICompatibleChatModel(c))
MODEL_PROVIDERS.register("open_router", lambda c: OpenRouterChatModel(c))
MODEL_PROVIDERS.register("openrouter", lambda c: OpenRouterChatModel(c))
MODEL_PROVIDERS.register("openrouter_reasoning", lambda c: OpenRouterChatModel(c))
MODEL_PROVIDERS.register("deepseek", lambda c: DeepSeekChatModel(c))
MODEL_PROVIDERS.register("siliconflow", lambda c: OpenAICompatibleChatModel(c))
MODEL_PROVIDERS.register("llama_api", lambda c: OpenAICompatibleChatModel(c))
MODEL_PROVIDERS.register("ollama", lambda c: OpenAICompatibleChatModel(c))
MODEL_PROVIDERS.register("qianfan", lambda c: QianfanChatModel(c))
MODEL_PROVIDERS.register("dashscope", lambda c: DashScopeChatModel(c))
MODEL_PROVIDERS.register("ark", lambda c: OpenAICompatibleChatModel(c))
MODEL_PROVIDERS.register("bedrock", lambda c: BedrockChatModel(c))
MODEL_PROVIDERS.register("gemini", lambda c: GeminiChatModel(c))
MODEL_PROVIDERS.register("zhipuai", lambda c: OpenAICompatibleChatModel(c))


def infer_provider_name(*, model: str, base_url: str | None) -> str:
    model_l = (model or "").lower()
    base_l = (base_url or "").lower()
    if "anthropic" in base_l or model_l.startswith("claude-"):
        return "anthropic"
    return "openai_compatible"


def normalize_provider_alias(provider: str | None) -> str | None:
    if provider is None:
        return None
    alias = provider.lower().strip()
    if alias in {"custom", "openai", "openai_compatible"}:
        return "openai_compatible"
    if alias in {"anthropic", "claude"}:
        return "anthropic"
    return alias


def create_chat_model(config: ModelConfig, *, provider: str | None = None) -> ChatModel:
    provider_name = provider or infer_provider_name(model=config.model, base_url=config.base_url)
    alias = normalize_provider_alias(provider_name) or "openai_compatible"
    if alias not in MODEL_PROVIDERS.names:
        alias = infer_provider_name(model=config.model, base_url=config.base_url)
    return MODEL_PROVIDERS.create(alias, config)
