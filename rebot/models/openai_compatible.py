"""OpenAI-compatible chat model adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
import asyncio
import json
import os
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Iterator, AsyncIterator, ClassVar, Callable

import httpx

from rebot.core.messages import Message
from rebot.models.base import _message_to_openai, _openai_to_message, _tool_to_openai
from rebot.models.config import ModelConfig
from rebot.models.retry import (
    compute_backoff_seconds,
    is_retryable_exception,
    is_retryable_status,
    next_retry_delay_seconds,
    sleep_backoff,
)
from rebot.tools.base import BaseTool


def _http_error_detail(resp: httpx.Response) -> str:
    try:
        text = (resp.text or "").strip()
    except Exception:
        text = ""
    if not text:
        return f"HTTP {resp.status_code}"
    if len(text) > 2000:
        text = text[:2000] + "...(truncated)"
    return f"HTTP {resp.status_code}: {text}"


def _sanitize_tool_call_sequence(messages: list[Message]) -> list[Message]:
    """Ensure assistant(tool_calls) and tool responses are emitted in valid pairs.

    Some providers (e.g. DeepSeek OpenAI-compatible endpoint) strictly require:
    assistant message with tool_calls -> immediate following tool messages for all ids.
    """
    out: list[Message] = []
    i = 0
    n = len(messages)
    while i < n:
        msg = messages[i]
        if msg.role == "tool":
            # Orphan tool message; skip.
            i += 1
            continue
        if msg.role == "assistant" and msg.tool_calls:
            expected = {str(tc.id) for tc in msg.tool_calls if tc.id}
            j = i + 1
            tools_block: list[Message] = []
            seen_ids: set[str] = set()
            while j < n and messages[j].role == "tool":
                tm = messages[j]
                tcid = tm.metadata.get("tool_call_id")
                if not tcid:
                    tcid = tm.name
                if tcid:
                    seen_ids.add(str(tcid))
                tools_block.append(tm)
                j += 1
            if expected and expected.issubset(seen_ids):
                out.append(msg)
                out.extend(tools_block)
            # If incomplete, drop this assistant tool-call block to avoid provider 400.
            i = j
            continue
        out.append(msg)
        i += 1
    return out


@dataclass
class OpenAICompatibleChatModel:
    config: ModelConfig
    supports_response_format: bool = True
    stream_callback: Callable[[Message], None] | None = None
    _sync_client: httpx.Client | None = field(default=None, init=False, repr=False)
    _async_client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)
    _rate_limiter_lock: ClassVar[threading.Lock] = threading.Lock()
    _last_request_ts: ClassVar[dict[str, float]] = {}
    _concurrency_lock: ClassVar[threading.Lock] = threading.Lock()
    _sync_semaphores: ClassVar[dict[str, threading.BoundedSemaphore]] = {}
    _async_semaphores: ClassVar[dict[tuple[str, int], asyncio.Semaphore]] = {}

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None:
            self._sync_client = httpx.Client(timeout=self.config.timeout_s)
        return self._sync_client

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=self.config.timeout_s)
        return self._async_client

    def _rate_limit_key(self) -> str:
        base = self.config.base_url or "https://api.openai.com/v1"
        return f"{base.rstrip('/')}::{self.config.model}"

    def _resolve_max_concurrency(self) -> int:
        env_v = os.getenv("REBOT_MODEL_MAX_CONCURRENCY")
        if env_v:
            try:
                return max(1, int(env_v))
            except Exception:
                pass
        return max(1, int(getattr(self.config, "max_concurrency", 2) or 2))

    def _concurrency_key(self) -> str:
        return f"{self._rate_limit_key()}::{self._resolve_max_concurrency()}"

    def _get_sync_semaphore(self) -> threading.BoundedSemaphore:
        key = self._concurrency_key()
        with self._concurrency_lock:
            sem = self._sync_semaphores.get(key)
            if sem is None:
                sem = threading.BoundedSemaphore(self._resolve_max_concurrency())
                self._sync_semaphores[key] = sem
            return sem

    async def _get_async_semaphore(self) -> asyncio.Semaphore:
        key = (self._concurrency_key(), id(asyncio.get_running_loop()))
        with self._concurrency_lock:
            sem = self._async_semaphores.get(key)
            if sem is None:
                sem = asyncio.Semaphore(self._resolve_max_concurrency())
                self._async_semaphores[key] = sem
            return sem

    @contextmanager
    def _sync_concurrency_slot(self):
        sem = self._get_sync_semaphore()
        sem.acquire()
        try:
            yield
        finally:
            sem.release()

    @asynccontextmanager
    async def _async_concurrency_slot(self):
        sem = await self._get_async_semaphore()
        await sem.acquire()
        try:
            yield
        finally:
            sem.release()

    def _is_deepseek(self) -> bool:
        base = (self.config.base_url or "").lower()
        return "api.deepseek.com" in base or self.config.model.startswith("deepseek-")

    def _normalize_response_format(self, response_format: Any) -> Any:
        if response_format is None:
            return None
        if not self._is_deepseek():
            return response_format
        # DeepSeek compatibility: JSON schema style may return 400 on chat/completions.
        # Downgrade to json_object while keeping strict JSON prompting in upper layers.
        if isinstance(response_format, dict) and response_format.get("type") == "json_schema":
            return {"type": "json_object"}
        return response_format

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
        prompt = int(usage.get("prompt_tokens") or 0)
        completion = int(usage.get("completion_tokens") or 0)
        total = int(usage.get("total_tokens") or (prompt + completion))
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
        }

    def invoke(self, messages: list[Message], *, tools: list[BaseTool], **kwargs: Any) -> Message:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [_message_to_openai(m) for m in _sanitize_tool_call_sequence(messages)],
        }
        response_format = self._normalize_response_format(kwargs.get("response_format"))
        if response_format is not None:
            payload["response_format"] = response_format
        if tools:
            payload["tools"] = [_tool_to_openai(t) for t in tools]
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.extra_headers:
            headers.update(self.config.extra_headers)
        base_url = self.config.base_url or "https://api.openai.com/v1"
        url = f"{base_url.rstrip('/')}/chat/completions"

        stream_cb = kwargs.get("stream_callback") or self.stream_callback
        for attempt in range(self.config.max_retries + 1):
            try:
                self._maybe_wait_for_rate_limit_sync()
                with self._sync_concurrency_slot():
                    if stream_cb is not None and not tools:
                        collected = self._invoke_stream_collect(
                            url=url,
                            headers=headers,
                            payload=payload,
                            stream_callback=stream_cb,
                        )
                        if collected is not None:
                            return Message(role="assistant", content=collected)
                    client = self._get_sync_client()
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 400 and self._is_deepseek() and "response_format" in payload:
                        payload.pop("response_format", None)
                        client = self._get_sync_client()
                        resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 429:
                    if attempt >= self.config.max_retries:
                        raise RuntimeError(_http_error_detail(resp))
                    delay_s = next_retry_delay_seconds(
                        attempt=attempt,
                        response_headers=resp.headers,
                        base_s=self.config.retry_base_s,
                        cap_s=self.config.retry_cap_s,
                    )
                    sleep_backoff(delay_s)
                    continue
                if resp.status_code >= 400:
                    raise RuntimeError(_http_error_detail(resp))
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})
                out = _openai_to_message(msg)
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
                if exc.response is not None:
                    raise RuntimeError(_http_error_detail(exc.response)) from exc
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
            "messages": [_message_to_openai(m) for m in _sanitize_tool_call_sequence(messages)],
        }
        response_format = self._normalize_response_format(kwargs.get("response_format"))
        if response_format is not None:
            payload["response_format"] = response_format
        if tools:
            payload["tools"] = [_tool_to_openai(t) for t in tools]
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.extra_headers:
            headers.update(self.config.extra_headers)
        base_url = self.config.base_url or "https://api.openai.com/v1"
        url = f"{base_url.rstrip('/')}/chat/completions"

        for attempt in range(self.config.max_retries + 1):
            try:
                await self._maybe_wait_for_rate_limit_async()
                stream_cb = kwargs.get("stream_callback") or self.stream_callback
                async with self._async_concurrency_slot():
                    if stream_cb is not None and not tools:
                        collected = await self._ainvoke_stream_collect(
                            url=url,
                            headers=headers,
                            payload=payload,
                            stream_callback=stream_cb,
                        )
                        if collected is not None:
                            return Message(role="assistant", content=collected)
                    client = self._get_async_client()
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 400 and self._is_deepseek() and "response_format" in payload:
                        payload.pop("response_format", None)
                        client = self._get_async_client()
                        resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 429:
                    if attempt >= self.config.max_retries:
                        raise RuntimeError(_http_error_detail(resp))
                    delay_s = next_retry_delay_seconds(
                        attempt=attempt,
                        response_headers=resp.headers,
                        base_s=self.config.retry_base_s,
                        cap_s=self.config.retry_cap_s,
                    )
                    await asyncio.sleep(delay_s)
                    continue
                if resp.status_code >= 400:
                    raise RuntimeError(_http_error_detail(resp))
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})
                out = _openai_to_message(msg)
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
                if exc.response is not None:
                    raise RuntimeError(_http_error_detail(exc.response)) from exc
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

    def _invoke_stream_collect(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        stream_callback: Callable[[Message], None],
    ) -> str | None:
        stream_payload = dict(payload)
        stream_payload["stream"] = True
        role = "assistant"
        collected: list[str] = []
        try:
            client = self._get_sync_client()
            with client.stream("POST", url, headers=headers, json=stream_payload) as resp:
                if resp.status_code == 429:
                    return None
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
                    except json.JSONDecodeError:
                        continue
                    delta = (data.get("choices", [{}])[0] or {}).get("delta", {}) or {}
                    if "role" in delta:
                        role = delta["role"]
                    content = delta.get("content")
                    if content:
                        collected.append(content)
                        stream_callback(Message(role=role, content=content))
            return "".join(collected)
        except Exception:
            return None

    async def _ainvoke_stream_collect(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        stream_callback: Callable[[Message], None],
    ) -> str | None:
        stream_payload = dict(payload)
        stream_payload["stream"] = True
        role = "assistant"
        collected: list[str] = []
        try:
            client = self._get_async_client()
            async with client.stream("POST", url, headers=headers, json=stream_payload) as resp:
                if resp.status_code == 429:
                    return None
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
                    except json.JSONDecodeError:
                        continue
                    delta = (data.get("choices", [{}])[0] or {}).get("delta", {}) or {}
                    if "role" in delta:
                        role = delta["role"]
                    content = delta.get("content")
                    if content:
                        collected.append(content)
                        stream_callback(Message(role=role, content=content))
            return "".join(collected)
        except Exception:
            return None

    def stream(
        self, messages: list[Message], *, tools: list[BaseTool], **kwargs: Any
    ) -> Iterator[Message]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [_message_to_openai(m) for m in _sanitize_tool_call_sequence(messages)],
            "stream": True,
        }
        response_format = self._normalize_response_format(kwargs.get("response_format"))
        if response_format is not None:
            payload["response_format"] = response_format
        if tools:
            payload["tools"] = [_tool_to_openai(t) for t in tools]
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.extra_headers:
            headers.update(self.config.extra_headers)
        base_url = self.config.base_url or "https://api.openai.com/v1"
        url = f"{base_url.rstrip('/')}/chat/completions"

        role = "assistant"
        self._maybe_wait_for_rate_limit_sync()
        with self._sync_concurrency_slot():
            client = self._get_sync_client()
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
                    except json.JSONDecodeError:
                        continue
                    delta = (data.get("choices", [{}])[0] or {}).get("delta", {}) or {}
                    if "role" in delta:
                        role = delta["role"]
                    if "content" in delta and delta["content"]:
                        yield Message(role=role, content=delta["content"])

    async def astream(
        self, messages: list[Message], *, tools: list[BaseTool], **kwargs: Any
    ) -> AsyncIterator[Message]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [_message_to_openai(m) for m in _sanitize_tool_call_sequence(messages)],
            "stream": True,
        }
        response_format = self._normalize_response_format(kwargs.get("response_format"))
        if response_format is not None:
            payload["response_format"] = response_format
        if tools:
            payload["tools"] = [_tool_to_openai(t) for t in tools]
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.extra_headers:
            headers.update(self.config.extra_headers)
        base_url = self.config.base_url or "https://api.openai.com/v1"
        url = f"{base_url.rstrip('/')}/chat/completions"

        role = "assistant"
        await self._maybe_wait_for_rate_limit_async()
        async with self._async_concurrency_slot():
            client = self._get_async_client()
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
                    except json.JSONDecodeError:
                        continue
                    delta = (data.get("choices", [{}])[0] or {}).get("delta", {}) or {}
                    if "role" in delta:
                        role = delta["role"]
                    if "content" in delta and delta["content"]:
                        yield Message(role=role, content=delta["content"])
