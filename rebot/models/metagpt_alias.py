"""MetaGPT-style provider adapters (thin wrappers)."""

from __future__ import annotations

from dataclasses import dataclass
import os

from rebot.models.config import ModelConfig
from rebot.models.openai_compatible import OpenAICompatibleChatModel


def _with_default_base(
    config: ModelConfig, default_base: str, *, extra_headers: dict[str, str] | None = None
) -> ModelConfig:
    if config.base_url:
        if extra_headers and not config.extra_headers:
            return ModelConfig(
                api_key=config.api_key,
                model=config.model,
                base_url=config.base_url,
                timeout_s=config.timeout_s,
                max_retries=config.max_retries,
                max_concurrency=config.max_concurrency,
                min_request_interval_s=config.min_request_interval_s,
                retry_base_s=config.retry_base_s,
                retry_cap_s=config.retry_cap_s,
                extra_headers=extra_headers,
            )
        return config
    return ModelConfig(
        api_key=config.api_key,
        model=config.model,
        base_url=default_base,
        timeout_s=config.timeout_s,
        max_retries=config.max_retries,
        max_concurrency=config.max_concurrency,
        min_request_interval_s=config.min_request_interval_s,
        retry_base_s=config.retry_base_s,
        retry_cap_s=config.retry_cap_s,
        extra_headers=extra_headers or config.extra_headers,
    )


@dataclass
class QianfanChatModel(OpenAICompatibleChatModel):
    def __init__(self, config: ModelConfig):
        super().__init__(_with_default_base(config, "https://qianfan.baidubce.com/v2"))


@dataclass
class DashScopeChatModel(OpenAICompatibleChatModel):
    def __init__(self, config: ModelConfig):
        super().__init__(_with_default_base(config, "https://dashscope.aliyuncs.com/compatible-mode/v1"))


@dataclass
class BedrockChatModel(OpenAICompatibleChatModel):
    def __init__(self, config: ModelConfig):
        super().__init__(_with_default_base(config, "https://bedrock-runtime.us-east-1.amazonaws.com"))


@dataclass
class GeminiChatModel(OpenAICompatibleChatModel):
    def __init__(self, config: ModelConfig):
        super().__init__(_with_default_base(config, "https://generativelanguage.googleapis.com/v1beta/openai"))


@dataclass
class DeepSeekChatModel(OpenAICompatibleChatModel):
    def __init__(self, config: ModelConfig):
        super().__init__(_with_default_base(config, "https://api.deepseek.com/v1"))


@dataclass
class MoonshotChatModel(OpenAICompatibleChatModel):
    def __init__(self, config: ModelConfig):
        super().__init__(_with_default_base(config, "https://api.moonshot.cn/v1"))


@dataclass
class OpenRouterChatModel(OpenAICompatibleChatModel):
    def __init__(self, config: ModelConfig):
        title = os.getenv("REBOT_OPENROUTER_APP_TITLE", "Rebot")
        referer = os.getenv("REBOT_OPENROUTER_HTTP_REFERER", "http://localhost")
        headers = {
            "HTTP-Referer": referer,
            "X-Title": title,
        }
        super().__init__(_with_default_base(config, "https://openrouter.ai/api/v1", extra_headers=headers))
