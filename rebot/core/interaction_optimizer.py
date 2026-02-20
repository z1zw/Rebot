from __future__ import annotations

import asyncio
import hashlib
import json
import time
import threading
from abc import ABC, abstractmethod
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any, Awaitable, Callable, Deque, Dict, Generic, 
    List, Optional, Set, Tuple, TypeVar, Union
)
import logging
from functools import lru_cache, wraps
import heapq

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class StreamingProtocol(str, Enum):
    SSE = "sse"
    WEBSOCKET = "websocket"
    GRPC_STREAM = "grpc_stream"
    LONG_POLLING = "long_polling"


@dataclass
class StreamChunk:
    id: str
    sequence: int
    content: str
    chunk_type: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    latency_ms: float = 0


@dataclass
class StreamMetrics:
    total_chunks: int = 0
    total_bytes: int = 0
    first_chunk_latency_ms: float = 0
    avg_chunk_latency_ms: float = 0
    throughput_chunks_per_sec: float = 0
    throughput_bytes_per_sec: float = 0
    start_time: float = field(default_factory=time.time)
    first_chunk_time: Optional[float] = None
    last_chunk_time: Optional[float] = None

    def record_chunk(self, chunk: StreamChunk):
        now = time.time()
        self.total_chunks += 1
        self.total_bytes += len(chunk.content.encode())
        
        if self.first_chunk_time is None:
            self.first_chunk_time = now
            self.first_chunk_latency_ms = (now - self.start_time) * 1000
        
        self.last_chunk_time = now
        elapsed = now - self.start_time
        if elapsed > 0:
            self.throughput_chunks_per_sec = self.total_chunks / elapsed
            self.throughput_bytes_per_sec = self.total_bytes / elapsed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_chunks": self.total_chunks,
            "total_bytes": self.total_bytes,
            "first_chunk_latency_ms": round(self.first_chunk_latency_ms, 2),
            "throughput_cps": round(self.throughput_chunks_per_sec, 2),
            "throughput_bps": round(self.throughput_bytes_per_sec, 2),
        }


class ChunkBuffer:
    def __init__(self, max_size: int = 1000, flush_interval: float = 0.05):
        self.max_size = max_size
        self.flush_interval = flush_interval
        self._buffer: Deque[StreamChunk] = deque(maxlen=max_size)
        self._lock = threading.RLock()
        self._last_flush = time.time()
        self._callbacks: List[Callable[[List[StreamChunk]], None]] = []

    def add(self, chunk: StreamChunk) -> bool:
        with self._lock:
            self._buffer.append(chunk)
            if self._should_flush():
                self._flush()
                return True
        return False

    def _should_flush(self) -> bool:
        if len(self._buffer) >= self.max_size:
            return True
        if time.time() - self._last_flush >= self.flush_interval:
            return True
        return False

    def _flush(self):
        if not self._buffer:
            return
        chunks = list(self._buffer)
        self._buffer.clear()
        self._last_flush = time.time()
        for cb in self._callbacks:
            try:
                cb(chunks)
            except Exception as e:
                logger.error(f"Flush callback error: {e}")

    def on_flush(self, callback: Callable[[List[StreamChunk]], None]):
        self._callbacks.append(callback)

    def force_flush(self):
        with self._lock:
            self._flush()


class DeltaAccumulator:
    def __init__(self, debounce_ms: float = 16.67):
        self.debounce_ms = debounce_ms
        self._pending: Dict[str, str] = {}
        self._last_emit: Dict[str, float] = {}
        self._lock = threading.RLock()

    def accumulate(self, key: str, delta: str) -> Optional[str]:
        now = time.time() * 1000
        with self._lock:
            self._pending[key] = self._pending.get(key, "") + delta
            last = self._last_emit.get(key, 0)
            
            if now - last >= self.debounce_ms:
                result = self._pending.pop(key, "")
                self._last_emit[key] = now
                return result if result else None
        return None

    def flush(self, key: str) -> Optional[str]:
        with self._lock:
            result = self._pending.pop(key, None)
            if result:
                self._last_emit[key] = time.time() * 1000
            return result

    def flush_all(self) -> Dict[str, str]:
        with self._lock:
            result = dict(self._pending)
            self._pending.clear()
            now = time.time() * 1000
            for k in result:
                self._last_emit[k] = now
            return result


class RequestDeduplicator:
    def __init__(self, window_ms: float = 100):
        self.window_ms = window_ms
        self._recent: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.RLock()

    def _hash_request(self, data: Any) -> str:
        if isinstance(data, str):
            return hashlib.md5(data.encode()).hexdigest()
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def should_process(self, request: Any) -> bool:
        now = time.time() * 1000
        key = self._hash_request(request)
        
        with self._lock:
            expired = []
            for k, t in self._recent.items():
                if now - t > self.window_ms:
                    expired.append(k)
                else:
                    break
            for k in expired:
                del self._recent[k]
            
            if key in self._recent:
                return False
            
            self._recent[key] = now
            return True


class RequestCoalescer(Generic[T, R]):
    def __init__(
        self,
        handler: Callable[[List[T]], Awaitable[List[R]]],
        max_batch: int = 10,
        max_wait_ms: float = 50
    ):
        self.handler = handler
        self.max_batch = max_batch
        self.max_wait_ms = max_wait_ms
        
        self._pending: List[Tuple[T, asyncio.Future]] = []
        self._lock = asyncio.Lock()
        self._timer: Optional[asyncio.TimerHandle] = None

    async def submit(self, request: T) -> R:
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        
        async with self._lock:
            self._pending.append((request, future))
            
            if len(self._pending) >= self.max_batch:
                await self._flush()
            elif self._timer is None:
                loop = asyncio.get_event_loop()
                self._timer = loop.call_later(
                    self.max_wait_ms / 1000,
                    lambda: asyncio.create_task(self._flush_safe())
                )
        
        return await future

    async def _flush_safe(self):
        try:
            async with self._lock:
                await self._flush()
        except Exception as e:
            logger.error(f"Coalescer flush error: {e}")

    async def _flush(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        
        if not self._pending:
            return
        
        batch = self._pending[:]
        self._pending = []
        
        requests = [r for r, _ in batch]
        futures = [f for _, f in batch]
        
        try:
            results = await self.handler(requests)
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)
        except Exception as e:
            for future in futures:
                if not future.done():
                    future.set_exception(e)


class LRUCache(Generic[T]):
    def __init__(self, max_size: int = 1000, ttl_seconds: float = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Tuple[T, float]] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[T]:
        with self._lock:
            if key not in self._cache:
                return None
            
            value, timestamp = self._cache[key]
            if time.time() - timestamp > self.ttl_seconds:
                del self._cache[key]
                return None
            
            self._cache.move_to_end(key)
            return value

    def put(self, key: str, value: T) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            
            self._cache[key] = (value, time.time())

    def invalidate(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


class PrefetchScheduler:
    def __init__(self, max_prefetch: int = 5):
        self.max_prefetch = max_prefetch
        self._queue: List[Tuple[float, str, Callable]] = []
        self._in_flight: Set[str] = set()
        self._lock = threading.RLock()

    def schedule(
        self,
        key: str,
        loader: Callable[[], Awaitable[Any]],
        priority: float = 0.5
    ):
        with self._lock:
            if key in self._in_flight:
                return
            if len(self._in_flight) >= self.max_prefetch:
                return
            heapq.heappush(self._queue, (-priority, key, loader))
            self._in_flight.add(key)

    async def run_next(self) -> Optional[Any]:
        with self._lock:
            if not self._queue:
                return None
            _, key, loader = heapq.heappop(self._queue)
        
        try:
            result = await loader()
            return result
        finally:
            with self._lock:
                self._in_flight.discard(key)

    async def run_all(self) -> List[Any]:
        results = []
        while self._queue:
            result = await self.run_next()
            if result is not None:
                results.append(result)
        return results


class OptimisticUpdater:
    def __init__(self):
        self._pending: Dict[str, Any] = {}
        self._confirmed: Dict[str, Any] = {}
        self._rollbacks: Dict[str, Callable] = {}
        self._lock = threading.RLock()

    def apply_optimistic(
        self,
        key: str,
        value: Any,
        rollback: Optional[Callable] = None
    ):
        with self._lock:
            self._pending[key] = value
            if rollback:
                self._rollbacks[key] = rollback

    def confirm(self, key: str, server_value: Optional[Any] = None):
        with self._lock:
            if key in self._pending:
                self._confirmed[key] = server_value or self._pending.pop(key)
                self._rollbacks.pop(key, None)

    def rollback(self, key: str):
        with self._lock:
            self._pending.pop(key, None)
            rollback_fn = self._rollbacks.pop(key, None)
            if rollback_fn:
                try:
                    rollback_fn()
                except Exception as e:
                    logger.error(f"Rollback error for {key}: {e}")

    def get_effective(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._pending:
                return self._pending[key]
            return self._confirmed.get(key)


@dataclass
class ThrottleConfig:
    requests_per_second: float = 10.0
    burst_size: int = 20
    retry_after_ms: float = 100


class TokenBucketThrottle:
    def __init__(self, config: ThrottleConfig):
        self.config = config
        self._tokens = config.burst_size
        self._last_refill = time.time()
        self._lock = threading.RLock()

    def _refill(self):
        now = time.time()
        elapsed = now - self._last_refill
        new_tokens = elapsed * self.config.requests_per_second
        self._tokens = min(self.config.burst_size, self._tokens + new_tokens)
        self._last_refill = now

    def acquire(self, tokens: int = 1) -> bool:
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    async def wait_and_acquire(self, tokens: int = 1) -> None:
        while not self.acquire(tokens):
            await asyncio.sleep(self.config.retry_after_ms / 1000)


class LatencyTracker:
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._samples: Deque[float] = deque(maxlen=window_size)
        self._lock = threading.RLock()

    def record(self, latency_ms: float):
        with self._lock:
            self._samples.append(latency_ms)

    @property
    def avg(self) -> float:
        with self._lock:
            if not self._samples:
                return 0.0
            return sum(self._samples) / len(self._samples)

    @property
    def p50(self) -> float:
        return self._percentile(50)

    @property
    def p95(self) -> float:
        return self._percentile(95)

    @property
    def p99(self) -> float:
        return self._percentile(99)

    def _percentile(self, p: float) -> float:
        with self._lock:
            if not self._samples:
                return 0.0
            sorted_samples = sorted(self._samples)
            idx = int(len(sorted_samples) * p / 100)
            return sorted_samples[min(idx, len(sorted_samples) - 1)]

    def to_dict(self) -> Dict[str, float]:
        return {
            "avg_ms": round(self.avg, 2),
            "p50_ms": round(self.p50, 2),
            "p95_ms": round(self.p95, 2),
            "p99_ms": round(self.p99, 2),
        }


class InteractionOptimizer:
    def __init__(
        self,
        debounce_ms: float = 16.67,
        max_batch: int = 10,
        cache_size: int = 1000,
        cache_ttl: float = 300
    ):
        self.delta_accumulator = DeltaAccumulator(debounce_ms)
        self.deduplicator = RequestDeduplicator(window_ms=100)
        self.cache = LRUCache(max_size=cache_size, ttl_seconds=cache_ttl)
        self.latency_tracker = LatencyTracker()
        self.prefetch = PrefetchScheduler()
        self.optimistic = OptimisticUpdater()
        self.throttle = TokenBucketThrottle(ThrottleConfig())
        
        self._metrics: Dict[str, Any] = {}

    def process_stream_delta(self, key: str, delta: str) -> Optional[str]:
        return self.delta_accumulator.accumulate(key, delta)

    def should_send_request(self, request: Any) -> bool:
        if not self.throttle.acquire():
            return False
        return self.deduplicator.should_process(request)

    def cache_response(self, key: str, response: Any):
        self.cache.put(key, response)

    def get_cached(self, key: str) -> Optional[Any]:
        return self.cache.get(key)

    def record_latency(self, latency_ms: float):
        self.latency_tracker.record(latency_ms)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "latency": self.latency_tracker.to_dict(),
            "cache_size": self.cache.size,
        }


def measure_latency(tracker: LatencyTracker):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                latency_ms = (time.time() - start) * 1000
                tracker.record(latency_ms)
        return wrapper
    return decorator


def with_cache(cache: LRUCache, key_func: Callable[..., str]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = key_func(*args, **kwargs)
            cached = cache.get(key)
            if cached is not None:
                return cached
            result = await func(*args, **kwargs)
            cache.put(key, result)
            return result
        return wrapper
    return decorator


class StreamOptimizer:
    def __init__(self):
        self.buffer = ChunkBuffer()
        self.metrics = StreamMetrics()
        self.latency = LatencyTracker()

    def process_chunk(self, chunk: StreamChunk) -> bool:
        self.metrics.record_chunk(chunk)
        self.latency.record(chunk.latency_ms)
        return self.buffer.add(chunk)

    def on_batch_ready(self, callback: Callable[[List[StreamChunk]], None]):
        self.buffer.on_flush(callback)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "stream": self.metrics.to_dict(),
            "latency": self.latency.to_dict(),
        }


def create_interaction_optimizer(
    debounce_ms: float = 16.67,
    cache_size: int = 1000
) -> InteractionOptimizer:
    return InteractionOptimizer(
        debounce_ms=debounce_ms,
        cache_size=cache_size
    )


def create_stream_optimizer() -> StreamOptimizer:
    return StreamOptimizer()
