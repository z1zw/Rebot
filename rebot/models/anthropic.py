"""Anthropic Claude chat model adapter."""

from __future__ import annotations

from dataclasses import dataclass
import asyncio
import json
import threading
import time
from typing import Any, Iterator, AsyncIterator, ClassVar

import httpx

from rebot.core.messages import Message
from rebot.models.config import ModelConfig
from rebot.models.retry import (
    compute_backoff_seconds,
    is_retryable_exception,
    is_retryable_status,
    next_retry_delay_seconds,
    sleep_backoff,
)
from rebot.tools.base import BaseTool


@dataclass
class AnthropicChatModel:
    config: ModelConfig
    supports_response_format: bool = False
    _rate_limiter_lock: ClassVar[threading.Lock] = threading.Lock()
    _last_request_ts: ClassVar[dict[str, float]] = {}

    def _rate_limit_key(self) -> str:
        base = self.config.base_url or "https://api.anthropic.com/v1"
        return f"{base.rstrip('/')}::{self.config.model}"

    def _maybe_wait_for_rate_limit_sync(self) -> None:
        interval = max(0.0, float(self.config.min_request_interval_s))
        if interval <= 0:
            return
        key = self._rate_limit_key()
        with self._rate_limiter_lock:
            prev = self._last_request_ts.get(key, 0.0)
            now = time.monotonic()
            wait_s = interval - (now - prev)
            if wait_s > 0:
                sleep_backoff(wait_s)
            self._last_request_ts[key] = time.monotonic()

    async def _maybe_wait_for_rate_limit_async(self) -> None:
        interval = max(0.0, float(self.config.min_request_interval_s))
        if interval <= 0:
            return
        key = self._rate_limit_key()
        with self._rate_limiter_lock:
            prev = self._last_request_ts.get(key, 0.0)
            now = time.monotonic()
            wait_s = interval - (now - prev)
        if wait_s > 0:
            await asyncio.sleep(wait_s)
        with self._rate_limiter_lock:
            self._last_request_ts[key] = time.monotonic()

    @staticmethod
    def _usage_from_response(data: dict[str, Any]) -> dict[str, int] | None:
        usage = data.get("usage")
        if not isinstance(usage, dict):
            return None
        prompt = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
        completion = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        total = int(usage.get("total_tokens") or (prompt + completion))
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
        }

    def invoke(self, messages: list[Message], *, tools: list[BaseTool], **kwargs: Any) -> Message:
        # Claude uses a different schema; we keep it minimal and compatible.
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in messages
                if m.role in {"user", "assistant"}
            ],
            "max_tokens": 1024,
        }
        if tools:
            payload["tools"] = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.input_schema,
                }
                for t in tools
            ]

        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        base_url = self.config.base_url or "https://api.anthropic.com/v1"
        url = f"{base_url.rstrip('/')}/messages"

        for attempt in range(self.config.max_retries + 1):
            try:
                self._maybe_wait_for_rate_limit_sync()
                with httpx.Client(timeout=self.config.timeout_s) as client:
                    resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 429:
                    if attempt >= self.config.max_retries:
                        resp.raise_for_status()
                    delay_s = next_retry_delay_seconds(
                        attempt=attempt,
                        response_headers=resp.headers,
                        base_s=self.config.retry_base_s,
                        cap_s=self.config.retry_cap_s,
                    )
                    sleep_backoff(delay_s)
                    continue
                resp.raise_for_status()
                data = resp.json()
                content = ""
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        content += block.get("text", "")
                out = Message(role="assistant", content=content)
                usage = self._usage_from_response(data)
                if usage:
                    out.metadata["usage"] = usage
                return out
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if is_retryable_status(status) and attempt < self.config.max_retries:
                    delay_s = next_retry_delay_seconds(
                        attempt=attempt,
                        response_headers=exc.response.headers if exc.response is not None else None,
                        base_s=self.config.retry_base_s,
                        cap_s=self.config.retry_cap_s,
                    )
                    sleep_backoff(delay_s)
                    continue
                raise
            except Exception as exc:
                if not is_retryable_exception(exc) or attempt >= self.config.max_retries:
                    raise
                delay_s = compute_backoff_seconds(
                    attempt,
                    base_s=self.config.retry_base_s,
                    cap_s=self.config.retry_cap_s,
                )
                sleep_backoff(delay_s)
                continue

    async def ainvoke(
        self, messages: list[Message], *, tools: list[BaseTool], **kwargs: Any
    ) -> Message:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in messages
                if m.role in {"user", "assistant"}
            ],
            "max_tokens": 1024,
        }
        if tools:
            payload["tools"] = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.input_schema,
                }
                for t in tools
            ]

        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        base_url = self.config.base_url or "https://api.anthropic.com/v1"
        url = f"{base_url.rstrip('/')}/messages"

        for attempt in range(self.config.max_retries + 1):
            try:
                await self._maybe_wait_for_rate_limit_async()
                async with httpx.AsyncClient(timeout=self.config.timeout_s) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 429:
                    if attempt >= self.config.max_retries:
                        resp.raise_for_status()
                    delay_s = next_retry_delay_seconds(
                        attempt=attempt,
                        response_headers=resp.headers,
                        base_s=self.config.retry_base_s,
                        cap_s=self.config.retry_cap_s,
                    )
                    await asyncio.sleep(delay_s)
                    continue
                resp.raise_for_status()
                data = resp.json()
                content = ""
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        content += block.get("text", "")
                out = Message(role="assistant", content=content)
                usage = self._usage_from_response(data)
                if usage:
                    out.metadata["usage"] = usage
                return out
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if is_retryable_status(status) and attempt < self.config.max_retries:
                    delay_s = next_retry_delay_seconds(
                        attempt=attempt,
                        response_headers=exc.response.headers if exc.response is not None else None,
                        base_s=self.config.retry_base_s,
                        cap_s=self.config.retry_cap_s,
                    )
                    await asyncio.sleep(delay_s)
                    continue
                raise
            except Exception as exc:
                if not is_retryable_exception(exc) or attempt >= self.config.max_retries:
                    raise
                delay_s = compute_backoff_seconds(
                    attempt,
                    base_s=self.config.retry_base_s,
                    cap_s=self.config.retry_cap_s,
                )
                await asyncio.sleep(delay_s)
                continue

    def stream(
        self, messages: list[Message], *, tools: list[BaseTool], **kwargs: Any
    ) -> Iterator[Message]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in messages
                if m.role in {"user", "assistant"}
            ],
            "max_tokens": 1024,
            "stream": True,
        }
        if tools:
            payload["tools"] = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.input_schema,
                }
                for t in tools
            ]

        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        base_url = self.config.base_url or "https://api.anthropic.com/v1"
        url = f"{base_url.rstrip('/')}/messages"

        with httpx.Client(timeout=self.config.timeout_s) as client:
            with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]":
                        break
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue
                    if data.get("type") == "content_block_delta":
                        delta = data.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                yield Message(role="assistant", content=text)

    async def astream(
        self, messages: list[Message], *, tools: list[BaseTool], **kwargs: Any
    ) -> AsyncIterator[Message]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in messages
                if m.role in {"user", "assistant"}
            ],
            "max_tokens": 1024,
            "stream": True,
        }
        if tools:
            payload["tools"] = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.input_schema,
                }
                for t in tools
            ]

        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        base_url = self.config.base_url or "https://api.anthropic.com/v1"
        url = f"{base_url.rstrip('/')}/messages"

        async with httpx.AsyncClient(timeout=self.config.timeout_s) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]":
                        break
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue
                    if data.get("type") == "content_block_delta":
                        delta = data.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                yield Message(role="assistant", content=text)
