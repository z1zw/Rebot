from __future__ import annotations

import asyncio
from typing import Any

from app.core.settings import settings


class BaseEventBus:
    async def publish(self, run_id: str, events: list[dict[str, Any]]) -> None:
        raise NotImplementedError

    async def publish_event(self, run_id: str, event: dict[str, Any]) -> None:
        await self.publish(run_id, [event])

    async def next(self) -> dict[str, Any]:
        raise NotImplementedError

    async def subscribe(self, run_id: str):
        raise NotImplementedError

    def unsubscribe(self, run_id: str, queue) -> None:
        raise NotImplementedError

    async def next_for_run(self, queue, timeout: float | None = None) -> dict[str, Any] | None:
        if timeout is None:
            return await queue.get()
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None


class InMemoryEventBus(BaseEventBus):
    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._run_queues: dict[str, set[asyncio.Queue]] = {}

    async def publish(self, run_id: str, events: list[dict[str, Any]]) -> None:
        if not events:
            return
        payload = {"run_id": run_id, "events": events}
        await self._queue.put(payload)
        for q in list(self._run_queues.get(run_id, set())):
            await q.put(payload)

    async def next(self) -> dict[str, Any]:
        return await self._queue.get()

    async def subscribe(self, run_id: str):
        q: asyncio.Queue = asyncio.Queue()
        self._run_queues.setdefault(run_id, set()).add(q)
        return q

    def unsubscribe(self, run_id: str, queue) -> None:
        queues = self._run_queues.get(run_id)
        if not queues:
            return
        queues.discard(queue)
        if not queues:
            self._run_queues.pop(run_id, None)


class RedisEventBus(BaseEventBus):
    def __init__(self, url: str) -> None:
        import redis.asyncio as redis

        self._redis = redis.from_url(url, decode_responses=True)
        self._channel = "rebot.events"
        self._fallback = InMemoryEventBus()
        self._pubsub = None
        self._listen_task: asyncio.Task | None = None
        self._listen_lock = asyncio.Lock()

    async def publish(self, run_id: str, events: list[dict[str, Any]]) -> None:
        if not events:
            return
        payload = {"run_id": run_id, "events": events}
        await self._fallback.publish(run_id, events)
        try:
            await self._redis.publish(self._channel, json_dumps(payload))
        except Exception:
            # Redis is best-effort for cross-process fanout.
            pass

    async def _ensure_pubsub(self):
        if self._pubsub is not None:
            return self._pubsub
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(self._channel)
        return self._pubsub

    async def _ensure_listener(self) -> None:
        if self._listen_task is not None and not self._listen_task.done():
            return
        async with self._listen_lock:
            if self._listen_task is not None and not self._listen_task.done():
                return
            self._listen_task = asyncio.create_task(self._listen_redis())

    async def _listen_redis(self) -> None:
        while True:
            try:
                pubsub = await self._ensure_pubsub()
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not msg:
                    await asyncio.sleep(0.05)
                    continue
                data = msg.get("data")
                if not data:
                    continue
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="ignore")
                payload = json_loads(str(data))
                run_id = str(payload.get("run_id") or "")
                events = payload.get("events") or []
                if run_id and events:
                    await self._fallback.publish(run_id, events)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.2)

    async def next(self) -> dict[str, Any]:
        # Prefer local queue first for low-latency same-process updates.
        try:
            return await asyncio.wait_for(self._fallback.next(), timeout=0.25)
        except asyncio.TimeoutError:
            pass
        try:
            pubsub = await self._ensure_pubsub()
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not msg:
                    await asyncio.sleep(0.05)
                    continue
                data = msg.get("data")
                if not data:
                    continue
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="ignore")
                return json_loads(str(data))
        except Exception:
            # If Redis read fails, continue with in-memory channel only.
            return await self._fallback.next()

    async def subscribe(self, run_id: str):
        await self._ensure_listener()
        return await self._fallback.subscribe(run_id)

    def unsubscribe(self, run_id: str, queue) -> None:
        self._fallback.unsubscribe(run_id, queue)

    async def next_for_run(self, queue, timeout: float | None = None) -> dict[str, Any] | None:
        return await self._fallback.next_for_run(queue, timeout=timeout)


def json_dumps(obj: Any) -> str:
    import json
    from dataclasses import asdict, is_dataclass

    def _default(value: Any):
        if is_dataclass(value):
            return asdict(value)
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "__dict__"):
            return value.__dict__
        return str(value)

    return json.dumps(obj, default=_default)


def json_loads(raw: str) -> dict[str, Any]:
    import json

    return json.loads(raw)


_BUS: BaseEventBus | None = None
_BUS_LOCK = asyncio.Lock()


async def _init_bus() -> BaseEventBus:
    if settings.redis_url:
        try:
            return RedisEventBus(settings.redis_url)
        except Exception:
            return InMemoryEventBus()
    return InMemoryEventBus()


def get_event_bus() -> BaseEventBus:
    global _BUS
    if _BUS is not None:
        return _BUS
    # Lazy init without requiring async caller.
    if settings.redis_url:
        try:
            _BUS = RedisEventBus(settings.redis_url)
            return _BUS
        except Exception:
            pass
    _BUS = InMemoryEventBus()
    return _BUS
