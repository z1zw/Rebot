from __future__ import annotations

import asyncio
import hashlib
import json
import time
import threading
from abc import ABC, abstractmethod
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any, AsyncGenerator, AsyncIterator, Awaitable, Callable, Deque, Dict,
    Generic, List, Optional, Set, Tuple, TypeVar, Union
)
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class StreamState(str, Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class StreamEvent:
    event_type: str
    data: Any
    sequence: int
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        return f"event: {self.event_type}\ndata: {json.dumps(self.data)}\n\n"


@dataclass
class StreamConfig:
    buffer_size: int = 1000
    batch_interval_ms: float = 50
    max_batch_size: int = 100
    reconnect_delay_ms: float = 1000
    max_reconnect_attempts: int = 5
    heartbeat_interval_ms: float = 30000
    compression_enabled: bool = False


@dataclass
class StreamStats:
    events_received: int = 0
    events_processed: int = 0
    events_dropped: int = 0
    bytes_received: int = 0
    reconnect_count: int = 0
    avg_latency_ms: float = 0.0
    peak_latency_ms: float = 0.0
    throughput_eps: float = 0.0
    start_time: float = field(default_factory=time.time)
    last_event_time: Optional[float] = None

    def record_event(self, event: StreamEvent, latency_ms: float):
        self.events_received += 1
        self.last_event_time = time.time()
        self.bytes_received += len(str(event.data))
        
        if latency_ms > self.peak_latency_ms:
            self.peak_latency_ms = latency_ms
        
        n = self.events_received
        self.avg_latency_ms = (self.avg_latency_ms * (n - 1) + latency_ms) / n
        
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            self.throughput_eps = self.events_received / elapsed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events_received": self.events_received,
            "events_processed": self.events_processed,
            "events_dropped": self.events_dropped,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "peak_latency_ms": round(self.peak_latency_ms, 2),
            "throughput_eps": round(self.throughput_eps, 2),
        }


class EventBuffer(Generic[T]):
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._buffer: Deque[T] = deque(maxlen=max_size)
        self._lock = threading.RLock()
        self._dropped = 0

    def push(self, item: T) -> bool:
        with self._lock:
            if len(self._buffer) >= self.max_size:
                self._dropped += 1
                return False
            self._buffer.append(item)
            return True

    def pop(self) -> Optional[T]:
        with self._lock:
            if self._buffer:
                return self._buffer.popleft()
            return None

    def pop_batch(self, max_count: int) -> List[T]:
        with self._lock:
            batch = []
            while self._buffer and len(batch) < max_count:
                batch.append(self._buffer.popleft())
            return batch

    def peek(self) -> Optional[T]:
        with self._lock:
            if self._buffer:
                return self._buffer[0]
            return None

    def clear(self) -> int:
        with self._lock:
            count = len(self._buffer)
            self._buffer.clear()
            return count

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def dropped_count(self) -> int:
        return self._dropped


class BackpressureController:
    def __init__(
        self,
        high_watermark: float = 0.8,
        low_watermark: float = 0.3,
        check_interval_ms: float = 100
    ):
        self.high_watermark = high_watermark
        self.low_watermark = low_watermark
        self.check_interval_ms = check_interval_ms
        self._paused = False
        self._pause_callbacks: List[Callable[[bool], None]] = []

    def check(self, buffer: EventBuffer) -> bool:
        fill_ratio = buffer.size / buffer.max_size
        
        if not self._paused and fill_ratio >= self.high_watermark:
            self._paused = True
            self._notify_pause(True)
            return True
        elif self._paused and fill_ratio <= self.low_watermark:
            self._paused = False
            self._notify_pause(False)
        
        return self._paused

    def on_pause_change(self, callback: Callable[[bool], None]):
        self._pause_callbacks.append(callback)

    def _notify_pause(self, paused: bool):
        for cb in self._pause_callbacks:
            try:
                cb(paused)
            except Exception as e:
                logger.error(f"Backpressure callback error: {e}")

    @property
    def is_paused(self) -> bool:
        return self._paused


class EventBatcher:
    def __init__(
        self,
        max_batch_size: int = 100,
        max_wait_ms: float = 50
    ):
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self._batch: List[StreamEvent] = []
        self._batch_start: Optional[float] = None
        self._lock = threading.RLock()

    def add(self, event: StreamEvent) -> Optional[List[StreamEvent]]:
        with self._lock:
            if self._batch_start is None:
                self._batch_start = time.time()
            
            self._batch.append(event)
            
            if self._should_flush():
                return self._flush()
        return None

    def _should_flush(self) -> bool:
        if len(self._batch) >= self.max_batch_size:
            return True
        if self._batch_start:
            elapsed_ms = (time.time() - self._batch_start) * 1000
            if elapsed_ms >= self.max_wait_ms:
                return True
        return False

    def _flush(self) -> List[StreamEvent]:
        batch = self._batch[:]
        self._batch = []
        self._batch_start = None
        return batch

    def force_flush(self) -> List[StreamEvent]:
        with self._lock:
            return self._flush()


class EventDeduplicator:
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self._seen: Dict[str, float] = {}
        self._order: Deque[str] = deque(maxlen=window_size)
        self._lock = threading.RLock()

    def _hash_event(self, event: StreamEvent) -> str:
        content = f"{event.event_type}:{event.sequence}:{json.dumps(event.data, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()

    def is_duplicate(self, event: StreamEvent) -> bool:
        event_hash = self._hash_event(event)
        
        with self._lock:
            if event_hash in self._seen:
                return True
            
            if len(self._order) >= self.window_size:
                old_hash = self._order[0]
                del self._seen[old_hash]
            
            self._seen[event_hash] = time.time()
            self._order.append(event_hash)
            
            return False


class EventRouter:
    def __init__(self):
        self._handlers: Dict[str, List[Callable[[StreamEvent], Awaitable[None]]]] = defaultdict(list)
        self._wildcards: List[Callable[[StreamEvent], Awaitable[None]]] = []

    def on(
        self,
        event_type: str,
        handler: Callable[[StreamEvent], Awaitable[None]]
    ):
        if event_type == "*":
            self._wildcards.append(handler)
        else:
            self._handlers[event_type].append(handler)

    async def route(self, event: StreamEvent):
        handlers = list(self._handlers.get(event.event_type, []))
        handlers.extend(self._wildcards)
        
        if not handlers:
            logger.debug(f"No handlers for event type: {event.event_type}")
            return
        
        tasks = [asyncio.create_task(h(event)) for h in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)


class RetryPolicy:
    def __init__(
        self,
        max_attempts: int = 5,
        base_delay_ms: float = 1000,
        max_delay_ms: float = 30000,
        exponential_base: float = 2.0
    ):
        self.max_attempts = max_attempts
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.exponential_base = exponential_base
        self._attempt = 0

    def next_delay_ms(self) -> Optional[float]:
        if self._attempt >= self.max_attempts:
            return None
        
        delay = self.base_delay_ms * (self.exponential_base ** self._attempt)
        delay = min(delay, self.max_delay_ms)
        self._attempt += 1
        
        return delay

    def reset(self):
        self._attempt = 0

    @property
    def attempts(self) -> int:
        return self._attempt


class StreamPipeline:
    def __init__(self, config: Optional[StreamConfig] = None):
        self.config = config or StreamConfig()
        self.state = StreamState.IDLE
        self.stats = StreamStats()
        
        self.buffer = EventBuffer(max_size=self.config.buffer_size)
        self.backpressure = BackpressureController()
        self.batcher = EventBatcher(
            max_batch_size=self.config.max_batch_size,
            max_wait_ms=self.config.batch_interval_ms
        )
        self.deduplicator = EventDeduplicator()
        self.router = EventRouter()
        self.retry_policy = RetryPolicy(
            max_attempts=self.config.max_reconnect_attempts,
            base_delay_ms=self.config.reconnect_delay_ms
        )
        
        self._sequence = 0
        self._lock = threading.RLock()
        self._running = False

    async def start(self, source: AsyncGenerator[StreamEvent, None]):
        self.state = StreamState.CONNECTING
        self._running = True
        self.retry_policy.reset()
        
        try:
            self.state = StreamState.STREAMING
            async for event in source:
                if not self._running:
                    break
                
                await self._process_event(event)
            
            self.state = StreamState.COMPLETED
        except Exception as e:
            self.state = StreamState.ERROR
            logger.error(f"Stream pipeline error: {e}")
            await self._handle_error(e, source)

    async def _process_event(self, event: StreamEvent):
        start_time = time.time()
        
        if self.deduplicator.is_duplicate(event):
            self.stats.events_dropped += 1
            return
        
        if self.backpressure.check(self.buffer):
            while self.backpressure.is_paused and self._running:
                await asyncio.sleep(0.01)
        
        self.buffer.push(event)
        
        batch = self.batcher.add(event)
        if batch:
            await self._process_batch(batch)
        
        latency_ms = (time.time() - start_time) * 1000
        self.stats.record_event(event, latency_ms)

    async def _process_batch(self, batch: List[StreamEvent]):
        for event in batch:
            try:
                await self.router.route(event)
                self.stats.events_processed += 1
            except Exception as e:
                logger.error(f"Event processing error: {e}")

    async def _handle_error(
        self,
        error: Exception,
        source: AsyncGenerator[StreamEvent, None]
    ):
        delay = self.retry_policy.next_delay_ms()
        if delay is None:
            logger.error("Max reconnect attempts reached")
            return
        
        self.stats.reconnect_count += 1
        logger.info(f"Reconnecting in {delay}ms...")
        await asyncio.sleep(delay / 1000)
        
        await self.start(source)

    def pause(self):
        if self.state == StreamState.STREAMING:
            self.state = StreamState.PAUSED

    def resume(self):
        if self.state == StreamState.PAUSED:
            self.state = StreamState.STREAMING

    async def stop(self):
        self._running = False
        remaining = self.batcher.force_flush()
        if remaining:
            await self._process_batch(remaining)
        
        self.state = StreamState.IDLE

    def on(
        self,
        event_type: str,
        handler: Callable[[StreamEvent], Awaitable[None]]
    ):
        self.router.on(event_type, handler)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "buffer_size": self.buffer.size,
            "buffer_dropped": self.buffer.dropped_count,
            "backpressure_paused": self.backpressure.is_paused,
            **self.stats.to_dict()
        }


class ChunkedTextStream:
    def __init__(
        self,
        chunk_size: int = 50,
        delay_ms: float = 16.67
    ):
        self.chunk_size = chunk_size
        self.delay_ms = delay_ms

    async def stream(
        self,
        text: str,
        on_chunk: Callable[[str], Awaitable[None]]
    ):
        for i in range(0, len(text), self.chunk_size):
            chunk = text[i:i + self.chunk_size]
            await on_chunk(chunk)
            await asyncio.sleep(self.delay_ms / 1000)


class DeltaMerger:
    def __init__(self):
        self._buffers: Dict[str, str] = {}
        self._lock = threading.RLock()

    def merge(self, stream_id: str, delta: str) -> str:
        with self._lock:
            self._buffers[stream_id] = self._buffers.get(stream_id, "") + delta
            return self._buffers[stream_id]

    def get(self, stream_id: str) -> str:
        with self._lock:
            return self._buffers.get(stream_id, "")

    def clear(self, stream_id: str) -> str:
        with self._lock:
            return self._buffers.pop(stream_id, "")

    def clear_all(self) -> Dict[str, str]:
        with self._lock:
            result = dict(self._buffers)
            self._buffers.clear()
            return result


class StreamTransformer(ABC, Generic[T, R]):
    @abstractmethod
    async def transform(self, item: T) -> R:
        pass


class JsonParseTransformer(StreamTransformer[str, Dict[str, Any]]):
    async def transform(self, item: str) -> Dict[str, Any]:
        try:
            return json.loads(item)
        except json.JSONDecodeError:
            return {"raw": item}


class SSEParseTransformer(StreamTransformer[str, StreamEvent]):
    def __init__(self):
        self._sequence = 0

    async def transform(self, item: str) -> StreamEvent:
        lines = item.strip().split("\n")
        event_type = "message"
        data = ""
        
        for line in lines:
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()
        
        self._sequence += 1
        return StreamEvent(
            event_type=event_type,
            data=data,
            sequence=self._sequence
        )


class TransformPipeline(Generic[T, R]):
    def __init__(self):
        self._transformers: List[StreamTransformer] = []

    def add(self, transformer: StreamTransformer) -> TransformPipeline:
        self._transformers.append(transformer)
        return self

    async def process(self, item: Any) -> Any:
        result = item
        for transformer in self._transformers:
            result = await transformer.transform(result)
        return result

    async def process_stream(
        self,
        source: AsyncIterator[T]
    ) -> AsyncGenerator[R, None]:
        async for item in source:
            yield await self.process(item)


def create_stream_pipeline(
    config: Optional[StreamConfig] = None
) -> StreamPipeline:
    return StreamPipeline(config)


def create_sse_transform_pipeline() -> TransformPipeline[str, StreamEvent]:
    pipeline = TransformPipeline()
    pipeline.add(SSEParseTransformer())
    return pipeline


def create_json_transform_pipeline() -> TransformPipeline[str, Dict[str, Any]]:
    pipeline = TransformPipeline()
    pipeline.add(JsonParseTransformer())
    return pipeline


class OptimizedStreamingPipeline:
    def __init__(self, config: Optional[StreamConfig] = None):
        self.pipeline = create_stream_pipeline(config)
        self.delta_merger = DeltaMerger()
        self.text_streamer = ChunkedTextStream()

    def on(
        self,
        event_type: str,
        handler: Callable[[StreamEvent], Awaitable[None]]
    ):
        self.pipeline.on(event_type, handler)

    async def start(self, source: AsyncGenerator[StreamEvent, None]):
        await self.pipeline.start(source)

    async def stop(self):
        await self.pipeline.stop()

    def merge_delta(self, stream_id: str, delta: str) -> str:
        return self.delta_merger.merge(stream_id, delta)

    async def stream_text(
        self,
        text: str,
        on_chunk: Callable[[str], Awaitable[None]]
    ):
        await self.text_streamer.stream(text, on_chunk)

    def get_stats(self) -> Dict[str, Any]:
        return self.pipeline.get_stats()


def create_optimized_streaming_pipeline(
    config: Optional[StreamConfig] = None
) -> OptimizedStreamingPipeline:
    return OptimizedStreamingPipeline(config)
