from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any, AsyncIterator, Callable, Dict, Iterator, List, 
    Optional, Protocol, Tuple, Type, TypeVar, Union
)
import threading
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

T = TypeVar("T")


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    DEEPSEEK = "deepseek"
    MOONSHOT = "moonshot"
    QIANFAN = "qianfan"
    DASHSCOPE = "dashscope"
    ZHIPU = "zhipu"
    MINIMAX = "minimax"
    BAICHUAN = "baichuan"
    YI = "yi"
    OLLAMA = "ollama"
    VLLM = "vllm"
    TOGETHER = "together"
    ANYSCALE = "anyscale"
    FIREWORKS = "fireworks"
    REPLICATE = "replicate"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"
    MISTRAL = "mistral"
    GROQ = "groq"
    PERPLEXITY = "perplexity"
    OPENROUTER = "openrouter"
    BEDROCK = "bedrock"
    SAGEMAKER = "sagemaker"
    VERTEX = "vertex"
    CUSTOM = "custom"


@dataclass
class ProviderConfig:
    provider: LLMProvider
    api_key: str = ""
    api_key_env: str = ""
    base_url: str = ""
    base_url_env: str = ""
    model: str = ""
    organization: str = ""
    project: str = ""
    region: str = ""
    timeout: float = 120.0
    max_retries: int = 3
    extra_headers: Dict[str, str] = field(default_factory=dict)
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def resolve_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            return os.environ.get(self.api_key_env, "")
        env_map = {
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            LLMProvider.GOOGLE: "GOOGLE_API_KEY",
            LLMProvider.AZURE: "AZURE_OPENAI_API_KEY",
            LLMProvider.DEEPSEEK: "DEEPSEEK_API_KEY",
            LLMProvider.MOONSHOT: "MOONSHOT_API_KEY",
            LLMProvider.QIANFAN: "QIANFAN_API_KEY",
            LLMProvider.DASHSCOPE: "DASHSCOPE_API_KEY",
            LLMProvider.ZHIPU: "ZHIPU_API_KEY",
            LLMProvider.MINIMAX: "MINIMAX_API_KEY",
            LLMProvider.BAICHUAN: "BAICHUAN_API_KEY",
            LLMProvider.YI: "YI_API_KEY",
            LLMProvider.TOGETHER: "TOGETHER_API_KEY",
            LLMProvider.ANYSCALE: "ANYSCALE_API_KEY",
            LLMProvider.FIREWORKS: "FIREWORKS_API_KEY",
            LLMProvider.REPLICATE: "REPLICATE_API_TOKEN",
            LLMProvider.HUGGINGFACE: "HUGGINGFACE_API_KEY",
            LLMProvider.COHERE: "COHERE_API_KEY",
            LLMProvider.MISTRAL: "MISTRAL_API_KEY",
            LLMProvider.GROQ: "GROQ_API_KEY",
            LLMProvider.PERPLEXITY: "PERPLEXITY_API_KEY",
            LLMProvider.OPENROUTER: "OPENROUTER_API_KEY",
        }
        env = env_map.get(self.provider, "")
        return os.environ.get(env, "") if env else ""

    def resolve_base_url(self) -> str:
        if self.base_url:
            return self.base_url
        if self.base_url_env:
            return os.environ.get(self.base_url_env, "")
        url_map = {
            LLMProvider.OPENAI: "https://api.openai.com/v1",
            LLMProvider.ANTHROPIC: "https://api.anthropic.com",
            LLMProvider.GOOGLE: "https://generativelanguage.googleapis.com/v1beta",
            LLMProvider.DEEPSEEK: "https://api.deepseek.com/v1",
            LLMProvider.MOONSHOT: "https://api.moonshot.cn/v1",
            LLMProvider.DASHSCOPE: "https://dashscope.aliyuncs.com/api/v1",
            LLMProvider.ZHIPU: "https://open.bigmodel.cn/api/paas/v4",
            LLMProvider.MINIMAX: "https://api.minimax.chat/v1",
            LLMProvider.BAICHUAN: "https://api.baichuan-ai.com/v1",
            LLMProvider.YI: "https://api.lingyiwanwu.com/v1",
            LLMProvider.TOGETHER: "https://api.together.xyz/v1",
            LLMProvider.ANYSCALE: "https://api.endpoints.anyscale.com/v1",
            LLMProvider.FIREWORKS: "https://api.fireworks.ai/inference/v1",
            LLMProvider.REPLICATE: "https://api.replicate.com/v1",
            LLMProvider.HUGGINGFACE: "https://api-inference.huggingface.co",
            LLMProvider.COHERE: "https://api.cohere.ai/v1",
            LLMProvider.MISTRAL: "https://api.mistral.ai/v1",
            LLMProvider.GROQ: "https://api.groq.com/openai/v1",
            LLMProvider.PERPLEXITY: "https://api.perplexity.ai",
            LLMProvider.OPENROUTER: "https://openrouter.ai/api/v1",
            LLMProvider.OLLAMA: "http://localhost:11434/v1",
            LLMProvider.VLLM: "http://localhost:8000/v1",
        }
        return url_map.get(self.provider, "")


@dataclass
class GenerationConfig:
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: int = 0
    max_tokens: int = 4096
    stop_sequences: List[str] = field(default_factory=list)
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    repetition_penalty: float = 1.0
    seed: Optional[int] = None
    logprobs: bool = False
    top_logprobs: int = 0
    json_mode: bool = False
    json_schema: Optional[Dict] = None

    def to_openai_params(self) -> Dict[str, Any]:
        params = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.top_p < 1.0:
            params["top_p"] = self.top_p
        if self.stop_sequences:
            params["stop"] = self.stop_sequences
        if self.presence_penalty != 0:
            params["presence_penalty"] = self.presence_penalty
        if self.frequency_penalty != 0:
            params["frequency_penalty"] = self.frequency_penalty
        if self.seed is not None:
            params["seed"] = self.seed
        if self.logprobs:
            params["logprobs"] = True
            params["top_logprobs"] = self.top_logprobs
        if self.json_mode:
            params["response_format"] = {"type": "json_object"}
        if self.json_schema:
            params["response_format"] = {
                "type": "json_schema",
                "json_schema": self.json_schema
            }
        return params

    def to_anthropic_params(self) -> Dict[str, Any]:
        params = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.top_p < 1.0:
            params["top_p"] = self.top_p
        if self.top_k > 0:
            params["top_k"] = self.top_k
        if self.stop_sequences:
            params["stop_sequences"] = self.stop_sequences
        return params


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    strict: bool = False

    def to_openai_format(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
                "strict": self.strict,
            }
        }

    def to_anthropic_format(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


@dataclass
class MessageContent:
    type: str = "text"
    text: str = ""
    image_url: str = ""
    image_base64: str = ""
    image_media_type: str = "image/png"
    tool_use_id: str = ""
    tool_name: str = ""
    tool_input: Dict = field(default_factory=dict)
    tool_result: Any = None


@dataclass
class ChatMessage:
    role: str
    content: Union[str, List[MessageContent]]
    name: Optional[str] = None
    tool_calls: List[Dict] = field(default_factory=list)
    tool_call_id: str = ""

    def to_openai_format(self) -> Dict[str, Any]:
        msg: Dict[str, Any] = {"role": self.role}
        if isinstance(self.content, str):
            msg["content"] = self.content
        else:
            parts = []
            for c in self.content:
                if c.type == "text":
                    parts.append({"type": "text", "text": c.text})
                elif c.type == "image":
                    if c.image_url:
                        parts.append({
                            "type": "image_url",
                            "image_url": {"url": c.image_url}
                        })
                    elif c.image_base64:
                        parts.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{c.image_media_type};base64,{c.image_base64}"
                            }
                        })
            msg["content"] = parts
        if self.name:
            msg["name"] = self.name
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        return msg

    def to_anthropic_format(self) -> Dict[str, Any]:
        msg: Dict[str, Any] = {"role": self.role}
        if isinstance(self.content, str):
            msg["content"] = self.content
        else:
            parts = []
            for c in self.content:
                if c.type == "text":
                    parts.append({"type": "text", "text": c.text})
                elif c.type == "image":
                    if c.image_base64:
                        parts.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": c.image_media_type,
                                "data": c.image_base64
                            }
                        })
                elif c.type == "tool_use":
                    parts.append({
                        "type": "tool_use",
                        "id": c.tool_use_id,
                        "name": c.tool_name,
                        "input": c.tool_input
                    })
                elif c.type == "tool_result":
                    parts.append({
                        "type": "tool_result",
                        "tool_use_id": c.tool_use_id,
                        "content": str(c.tool_result)
                    })
            msg["content"] = parts
        return msg


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0


@dataclass
class ChatCompletion:
    id: str
    model: str
    content: str
    finish_reason: str
    tool_calls: List[Dict] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: float = 0
    raw_response: Dict = field(default_factory=dict)


class BaseLLMAdapter(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self._http_client = None
        self._async_client = None

    @abstractmethod
    def complete(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: str = "auto"
    ) -> ChatCompletion:
        pass

    @abstractmethod
    async def acomplete(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: str = "auto"
    ) -> ChatCompletion:
        pass

    @abstractmethod
    def stream(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> Iterator[str]:
        pass

    @abstractmethod
    async def astream(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> AsyncIterator[str]:
        pass

    def _ensure_http_client(self):
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.Client(
                    timeout=self.config.timeout,
                    headers=self.config.extra_headers
                )
            except ImportError:
                import urllib.request
                self._http_client = "urllib"
        return self._http_client

    async def _ensure_async_client(self):
        if self._async_client is None:
            try:
                import httpx
                self._async_client = httpx.AsyncClient(
                    timeout=self.config.timeout,
                    headers=self.config.extra_headers
                )
            except ImportError:
                import aiohttp
                self._async_client = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
        return self._async_client

    def _post_json(self, url: str, data: Dict, headers: Dict) -> Dict:
        client = self._ensure_http_client()
        if client == "urllib":
            import urllib.request
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={**headers, "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                return json.loads(resp.read().decode())
        else:
            resp = client.post(url, json=data, headers=headers)
            resp.raise_for_status()
            return resp.json()


class OpenAIAdapter(BaseLLMAdapter):
    def complete(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: str = "auto"
    ) -> ChatCompletion:
        start = time.time()
        url = f"{self.config.resolve_base_url()}/chat/completions"
        headers = {"Authorization": f"Bearer {self.config.resolve_api_key()}"}
        
        body: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [m.to_openai_format() for m in messages],
            **gen_config.to_openai_params()
        }
        if tools:
            body["tools"] = [t.to_openai_format() for t in tools]
            body["tool_choice"] = tool_choice

        resp = self._post_json(url, body, headers)
        choice = resp.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = resp.get("usage", {})

        return ChatCompletion(
            id=resp.get("id", ""),
            model=resp.get("model", self.config.model),
            content=message.get("content", "") or "",
            finish_reason=choice.get("finish_reason", ""),
            tool_calls=message.get("tool_calls", []),
            usage=TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                cached_tokens=usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
            ),
            latency_ms=(time.time() - start) * 1000,
            raw_response=resp
        )

    async def acomplete(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: str = "auto"
    ) -> ChatCompletion:
        return await asyncio.to_thread(
            self.complete, messages, gen_config, tools, tool_choice
        )

    def stream(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> Iterator[str]:
        url = f"{self.config.resolve_base_url()}/chat/completions"
        headers = {"Authorization": f"Bearer {self.config.resolve_api_key()}"}
        body: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [m.to_openai_format() for m in messages],
            "stream": True,
            **gen_config.to_openai_params()
        }
        if tools:
            body["tools"] = [t.to_openai_format() for t in tools]

        try:
            import httpx
            with httpx.stream("POST", url, json=body, headers=headers, timeout=self.config.timeout) as resp:
                for line in resp.iter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data = json.loads(line[6:])
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        if content := delta.get("content"):
                            yield content
        except ImportError:
            resp = self.complete(messages, gen_config, tools)
            yield resp.content

    async def astream(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> AsyncIterator[str]:
        for chunk in self.stream(messages, gen_config, tools):
            yield chunk


class AnthropicAdapter(BaseLLMAdapter):
    def complete(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: str = "auto"
    ) -> ChatCompletion:
        start = time.time()
        url = f"{self.config.resolve_base_url()}/v1/messages"
        headers = {
            "x-api-key": self.config.resolve_api_key(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        system_content = ""
        conv_messages = []
        for m in messages:
            if m.role == "system":
                system_content = m.content if isinstance(m.content, str) else ""
            else:
                conv_messages.append(m.to_anthropic_format())

        body: Dict[str, Any] = {
            "model": self.config.model,
            "messages": conv_messages,
            **gen_config.to_anthropic_params()
        }
        if system_content:
            body["system"] = system_content
        if tools:
            body["tools"] = [t.to_anthropic_format() for t in tools]
            if tool_choice == "required":
                body["tool_choice"] = {"type": "any"}
            elif tool_choice != "auto":
                body["tool_choice"] = {"type": "tool", "name": tool_choice}

        resp = self._post_json(url, body, headers)
        content_blocks = resp.get("content", [])
        text_parts = []
        tool_calls = []
        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id"),
                    "type": "function",
                    "function": {
                        "name": block.get("name"),
                        "arguments": json.dumps(block.get("input", {}))
                    }
                })

        usage = resp.get("usage", {})
        return ChatCompletion(
            id=resp.get("id", ""),
            model=resp.get("model", self.config.model),
            content="".join(text_parts),
            finish_reason=resp.get("stop_reason", ""),
            tool_calls=tool_calls,
            usage=TokenUsage(
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                cached_tokens=usage.get("cache_read_input_tokens", 0)
            ),
            latency_ms=(time.time() - start) * 1000,
            raw_response=resp
        )

    async def acomplete(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: str = "auto"
    ) -> ChatCompletion:
        return await asyncio.to_thread(
            self.complete, messages, gen_config, tools, tool_choice
        )

    def stream(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> Iterator[str]:
        url = f"{self.config.resolve_base_url()}/v1/messages"
        headers = {
            "x-api-key": self.config.resolve_api_key(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        system_content = ""
        conv_messages = []
        for m in messages:
            if m.role == "system":
                system_content = m.content if isinstance(m.content, str) else ""
            else:
                conv_messages.append(m.to_anthropic_format())

        body: Dict[str, Any] = {
            "model": self.config.model,
            "messages": conv_messages,
            "stream": True,
            **gen_config.to_anthropic_params()
        }
        if system_content:
            body["system"] = system_content
        if tools:
            body["tools"] = [t.to_anthropic_format() for t in tools]

        try:
            import httpx
            with httpx.stream("POST", url, json=body, headers=headers, timeout=self.config.timeout) as resp:
                for line in resp.iter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if text := delta.get("text"):
                                yield text
        except ImportError:
            resp = self.complete(messages, gen_config, tools)
            yield resp.content

    async def astream(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> AsyncIterator[str]:
        for chunk in self.stream(messages, gen_config, tools):
            yield chunk


class GoogleAdapter(BaseLLMAdapter):
    def complete(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: str = "auto"
    ) -> ChatCompletion:
        start = time.time()
        model = self.config.model or "gemini-1.5-pro"
        url = f"{self.config.resolve_base_url()}/models/{model}:generateContent?key={self.config.resolve_api_key()}"
        
        parts = []
        system_instruction = None
        for m in messages:
            if m.role == "system":
                system_instruction = m.content if isinstance(m.content, str) else ""
            else:
                role = "user" if m.role == "user" else "model"
                content = m.content if isinstance(m.content, str) else m.content[0].text
                parts.append({"role": role, "parts": [{"text": content}]})

        body: Dict[str, Any] = {
            "contents": parts,
            "generationConfig": {
                "temperature": gen_config.temperature,
                "topP": gen_config.top_p,
                "topK": gen_config.top_k if gen_config.top_k > 0 else 40,
                "maxOutputTokens": gen_config.max_tokens,
            }
        }
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        if tools:
            body["tools"] = [{
                "functionDeclarations": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters
                    }
                    for t in tools
                ]
            }]

        resp = self._post_json(url, body, {})
        candidates = resp.get("candidates", [{}])
        content_parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in content_parts if "text" in p)
        
        tool_calls = []
        for p in content_parts:
            if "functionCall" in p:
                fc = p["functionCall"]
                tool_calls.append({
                    "id": hashlib.md5(fc["name"].encode()).hexdigest()[:8],
                    "type": "function",
                    "function": {
                        "name": fc["name"],
                        "arguments": json.dumps(fc.get("args", {}))
                    }
                })

        usage_meta = resp.get("usageMetadata", {})
        return ChatCompletion(
            id=hashlib.md5(json.dumps(resp).encode()).hexdigest()[:16],
            model=model,
            content=text,
            finish_reason=candidates[0].get("finishReason", ""),
            tool_calls=tool_calls,
            usage=TokenUsage(
                prompt_tokens=usage_meta.get("promptTokenCount", 0),
                completion_tokens=usage_meta.get("candidatesTokenCount", 0),
                total_tokens=usage_meta.get("totalTokenCount", 0)
            ),
            latency_ms=(time.time() - start) * 1000,
            raw_response=resp
        )

    async def acomplete(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: str = "auto"
    ) -> ChatCompletion:
        return await asyncio.to_thread(
            self.complete, messages, gen_config, tools, tool_choice
        )

    def stream(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> Iterator[str]:
        resp = self.complete(messages, gen_config, tools)
        yield resp.content

    async def astream(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> AsyncIterator[str]:
        for chunk in self.stream(messages, gen_config, tools):
            yield chunk


class CohereAdapter(BaseLLMAdapter):
    def complete(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: str = "auto"
    ) -> ChatCompletion:
        start = time.time()
        url = f"{self.config.resolve_base_url()}/chat"
        headers = {"Authorization": f"Bearer {self.config.resolve_api_key()}"}

        chat_history = []
        message = ""
        preamble = ""
        for m in messages:
            content = m.content if isinstance(m.content, str) else m.content[0].text
            if m.role == "system":
                preamble = content
            elif m.role == "user":
                message = content
            else:
                chat_history.append({
                    "role": "CHATBOT" if m.role == "assistant" else "USER",
                    "message": content
                })

        body: Dict[str, Any] = {
            "model": self.config.model,
            "message": message,
            "temperature": gen_config.temperature,
            "max_tokens": gen_config.max_tokens,
        }
        if preamble:
            body["preamble"] = preamble
        if chat_history:
            body["chat_history"] = chat_history
        if tools:
            body["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "parameter_definitions": t.parameters.get("properties", {})
                }
                for t in tools
            ]

        resp = self._post_json(url, body, headers)
        tool_calls = []
        for tc in resp.get("tool_calls", []):
            tool_calls.append({
                "id": tc.get("id", ""),
                "type": "function",
                "function": {
                    "name": tc.get("name", ""),
                    "arguments": json.dumps(tc.get("parameters", {}))
                }
            })

        return ChatCompletion(
            id=resp.get("generation_id", ""),
            model=self.config.model,
            content=resp.get("text", ""),
            finish_reason=resp.get("finish_reason", ""),
            tool_calls=tool_calls,
            usage=TokenUsage(
                prompt_tokens=resp.get("meta", {}).get("tokens", {}).get("input_tokens", 0),
                completion_tokens=resp.get("meta", {}).get("tokens", {}).get("output_tokens", 0)
            ),
            latency_ms=(time.time() - start) * 1000,
            raw_response=resp
        )

    async def acomplete(
        self,
        messages: List[ChatMessage],
        gen_config: GenerationConfig,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: str = "auto"
    ) -> ChatCompletion:
        return await asyncio.to_thread(
            self.complete, messages, gen_config, tools, tool_choice
        )

    def stream(self, messages, gen_config, tools=None) -> Iterator[str]:
        resp = self.complete(messages, gen_config, tools)
        yield resp.content

    async def astream(self, messages, gen_config, tools=None) -> AsyncIterator[str]:
        for chunk in self.stream(messages, gen_config, tools):
            yield chunk


ADAPTER_MAP: Dict[LLMProvider, Type[BaseLLMAdapter]] = {
    LLMProvider.OPENAI: OpenAIAdapter,
    LLMProvider.AZURE: OpenAIAdapter,
    LLMProvider.DEEPSEEK: OpenAIAdapter,
    LLMProvider.MOONSHOT: OpenAIAdapter,
    LLMProvider.ZHIPU: OpenAIAdapter,
    LLMProvider.MINIMAX: OpenAIAdapter,
    LLMProvider.BAICHUAN: OpenAIAdapter,
    LLMProvider.YI: OpenAIAdapter,
    LLMProvider.TOGETHER: OpenAIAdapter,
    LLMProvider.ANYSCALE: OpenAIAdapter,
    LLMProvider.FIREWORKS: OpenAIAdapter,
    LLMProvider.GROQ: OpenAIAdapter,
    LLMProvider.PERPLEXITY: OpenAIAdapter,
    LLMProvider.OPENROUTER: OpenAIAdapter,
    LLMProvider.OLLAMA: OpenAIAdapter,
    LLMProvider.VLLM: OpenAIAdapter,
    LLMProvider.MISTRAL: OpenAIAdapter,
    LLMProvider.ANTHROPIC: AnthropicAdapter,
    LLMProvider.BEDROCK: AnthropicAdapter,
    LLMProvider.GOOGLE: GoogleAdapter,
    LLMProvider.VERTEX: GoogleAdapter,
    LLMProvider.COHERE: CohereAdapter,
    LLMProvider.CUSTOM: OpenAIAdapter,
}


class UniversalLLM:
    def __init__(
        self,
        provider: Union[str, LLMProvider] = LLMProvider.OPENAI,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
        **kwargs
    ):
        if isinstance(provider, str):
            provider = LLMProvider(provider.lower())
        
        self.provider_config = ProviderConfig(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model,
            **{k: v for k, v in kwargs.items() if hasattr(ProviderConfig, k)}
        )
        
        adapter_class = ADAPTER_MAP.get(provider, OpenAIAdapter)
        self.adapter = adapter_class(self.provider_config)
        self.default_gen_config = GenerationConfig()

    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        **kwargs
    ) -> ChatCompletion:
        chat_messages = []
        for m in messages:
            chat_messages.append(ChatMessage(
                role=m.get("role", "user"),
                content=m.get("content", ""),
                name=m.get("name"),
                tool_calls=m.get("tool_calls", []),
                tool_call_id=m.get("tool_call_id", "")
            ))

        tool_defs = None
        if tools:
            tool_defs = []
            for t in tools:
                fn = t.get("function", t)
                tool_defs.append(ToolDefinition(
                    name=fn.get("name", ""),
                    description=fn.get("description", ""),
                    parameters=fn.get("parameters", {}),
                    strict=fn.get("strict", False)
                ))

        gen_config = GenerationConfig(
            temperature=temperature,
            max_tokens=max_tokens,
            **{k: v for k, v in kwargs.items() if hasattr(GenerationConfig, k)}
        )

        return self.adapter.complete(chat_messages, gen_config, tool_defs, tool_choice)

    async def achat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        **kwargs
    ) -> ChatCompletion:
        chat_messages = []
        for m in messages:
            chat_messages.append(ChatMessage(
                role=m.get("role", "user"),
                content=m.get("content", ""),
                name=m.get("name"),
                tool_calls=m.get("tool_calls", []),
                tool_call_id=m.get("tool_call_id", "")
            ))

        tool_defs = None
        if tools:
            tool_defs = []
            for t in tools:
                fn = t.get("function", t)
                tool_defs.append(ToolDefinition(
                    name=fn.get("name", ""),
                    description=fn.get("description", ""),
                    parameters=fn.get("parameters", {}),
                    strict=fn.get("strict", False)
                ))

        gen_config = GenerationConfig(
            temperature=temperature,
            max_tokens=max_tokens,
            **{k: v for k, v in kwargs.items() if hasattr(GenerationConfig, k)}
        )

        return await self.adapter.acomplete(chat_messages, gen_config, tool_defs, tool_choice)

    def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Iterator[str]:
        chat_messages = [
            ChatMessage(
                role=m.get("role", "user"),
                content=m.get("content", "")
            )
            for m in messages
        ]
        gen_config = GenerationConfig(temperature=temperature, max_tokens=max_tokens)
        tool_defs = None
        if tools:
            tool_defs = [
                ToolDefinition(
                    name=t.get("function", t).get("name", ""),
                    description=t.get("function", t).get("description", ""),
                    parameters=t.get("function", t).get("parameters", {})
                )
                for t in tools
            ]
        return self.adapter.stream(chat_messages, gen_config, tool_defs)

    async def astream_chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        chat_messages = [
            ChatMessage(role=m.get("role", "user"), content=m.get("content", ""))
            for m in messages
        ]
        gen_config = GenerationConfig(temperature=temperature, max_tokens=max_tokens)
        tool_defs = None
        if tools:
            tool_defs = [
                ToolDefinition(
                    name=t.get("function", t).get("name", ""),
                    description=t.get("function", t).get("description", ""),
                    parameters=t.get("function", t).get("parameters", {})
                )
                for t in tools
            ]
        async for chunk in self.adapter.astream(chat_messages, gen_config, tool_defs):
            yield chunk


class LLMRegistry:
    _instances: Dict[str, UniversalLLM] = {}
    _lock = threading.RLock()

    @classmethod
    def register(cls, name: str, llm: UniversalLLM) -> None:
        with cls._lock:
            cls._instances[name] = llm

    @classmethod
    def get(cls, name: str) -> Optional[UniversalLLM]:
        return cls._instances.get(name)

    @classmethod
    def create(
        cls,
        name: str,
        provider: Union[str, LLMProvider],
        **kwargs
    ) -> UniversalLLM:
        llm = UniversalLLM(provider=provider, **kwargs)
        cls.register(name, llm)
        return llm

    @classmethod
    def list_providers(cls) -> List[str]:
        return [p.value for p in LLMProvider]


def create_llm(
    provider: str,
    model: str = "",
    api_key: str = "",
    base_url: str = "",
    **kwargs
) -> UniversalLLM:
    return UniversalLLM(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        **kwargs
    )
