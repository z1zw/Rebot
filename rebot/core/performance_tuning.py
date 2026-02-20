from __future__ import annotations

import asyncio
import hashlib
import json
import time
import threading
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any, Awaitable, Callable, Deque, Dict, Generic,
    List, Optional, Set, Tuple, TypeVar, Union
)
import logging
import os
import sys

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PerformanceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


@dataclass
class SystemCapabilities:
    cpu_cores: int = 4
    memory_gb: float = 8.0
    has_gpu: bool = False
    gpu_memory_gb: float = 0.0
    network_latency_ms: float = 50.0
    storage_type: str = "ssd"

    @classmethod
    def detect(cls) -> SystemCapabilities:
        import multiprocessing
        cores = multiprocessing.cpu_count()
        
        try:
            import psutil
            memory_gb = psutil.virtual_memory().total / (1024 ** 3)
        except ImportError:
            memory_gb = 8.0
        
        has_gpu = False
        gpu_memory = 0.0
        try:
            import torch
            has_gpu = torch.cuda.is_available()
            if has_gpu:
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        except ImportError:
            pass
        
        return cls(
            cpu_cores=cores,
            memory_gb=memory_gb,
            has_gpu=has_gpu,
            gpu_memory_gb=gpu_memory
        )

    def get_performance_level(self) -> PerformanceLevel:
        if self.cpu_cores >= 8 and self.memory_gb >= 32:
            return PerformanceLevel.ULTRA
        elif self.cpu_cores >= 6 and self.memory_gb >= 16:
            return PerformanceLevel.HIGH
        elif self.cpu_cores >= 4 and self.memory_gb >= 8:
            return PerformanceLevel.MEDIUM
        return PerformanceLevel.LOW


@dataclass
class PerformanceConfig:
    level: PerformanceLevel = PerformanceLevel.MEDIUM
    
    max_concurrent_requests: int = 10
    request_timeout_ms: float = 30000
    batch_size: int = 10
    
    cache_size_mb: float = 256
    cache_ttl_seconds: float = 300
    
    stream_buffer_size: int = 1000
    stream_batch_interval_ms: float = 50
    
    render_fps: int = 60
    animation_duration_ms: float = 200
    typing_speed_cps: float = 60
    
    worker_threads: int = 4
    io_pool_size: int = 8

    @classmethod
    def from_capabilities(cls, caps: SystemCapabilities) -> PerformanceConfig:
        level = caps.get_performance_level()
        
        configs = {
            PerformanceLevel.LOW: cls(
                level=level,
                max_concurrent_requests=5,
                batch_size=5,
                cache_size_mb=64,
                stream_buffer_size=500,
                render_fps=30,
                worker_threads=2,
                io_pool_size=4
            ),
            PerformanceLevel.MEDIUM: cls(
                level=level,
                max_concurrent_requests=10,
                batch_size=10,
                cache_size_mb=256,
                stream_buffer_size=1000,
                render_fps=60,
                worker_threads=4,
                io_pool_size=8
            ),
            PerformanceLevel.HIGH: cls(
                level=level,
                max_concurrent_requests=20,
                batch_size=20,
                cache_size_mb=512,
                stream_buffer_size=2000,
                render_fps=60,
                worker_threads=8,
                io_pool_size=16
            ),
            PerformanceLevel.ULTRA: cls(
                level=level,
                max_concurrent_requests=50,
                batch_size=50,
                cache_size_mb=1024,
                stream_buffer_size=5000,
                render_fps=120,
                worker_threads=12,
                io_pool_size=24
            ),
        }
        
        return configs[level]


@dataclass
class MetricSample:
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsRegistry:
    def __init__(self):
        self._metrics: Dict[str, Deque[MetricSample]] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = threading.RLock()

    def record(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        sample = MetricSample(value=value, labels=labels or {})
        with self._lock:
            self._metrics[name].append(sample)

    def get_latest(self, name: str) -> Optional[float]:
        with self._lock:
            samples = self._metrics.get(name)
            if samples:
                return samples[-1].value
        return None

    def get_average(self, name: str, window_seconds: float = 60) -> Optional[float]:
        with self._lock:
            samples = self._metrics.get(name)
            if not samples:
                return None
            
            cutoff = time.time() - window_seconds
            recent = [s.value for s in samples if s.timestamp >= cutoff]
            
            if not recent:
                return None
            
            return sum(recent) / len(recent)

    def get_percentile(
        self,
        name: str,
        percentile: float,
        window_seconds: float = 60
    ) -> Optional[float]:
        with self._lock:
            samples = self._metrics.get(name)
            if not samples:
                return None
            
            cutoff = time.time() - window_seconds
            recent = sorted([s.value for s in samples if s.timestamp >= cutoff])
            
            if not recent:
                return None
            
            idx = int(len(recent) * percentile / 100)
            return recent[min(idx, len(recent) - 1)]

    def get_all_metrics(self) -> Dict[str, Dict[str, float]]:
        result = {}
        with self._lock:
            for name in self._metrics:
                avg = self.get_average(name)
                p50 = self.get_percentile(name, 50)
                p95 = self.get_percentile(name, 95)
                p99 = self.get_percentile(name, 99)
                
                if avg is not None:
                    result[name] = {
                        "avg": round(avg, 3),
                        "p50": round(p50 or 0, 3),
                        "p95": round(p95 or 0, 3),
                        "p99": round(p99 or 0, 3),
                    }
        return result


class PerformanceProfiler:
    def __init__(self, registry: Optional[MetricsRegistry] = None):
        self.registry = registry or MetricsRegistry()
        self._active_spans: Dict[str, float] = {}
        self._lock = threading.RLock()

    def start_span(self, name: str) -> str:
        span_id = f"{name}_{time.time_ns()}"
        with self._lock:
            self._active_spans[span_id] = time.time()
        return span_id

    def end_span(self, span_id: str):
        with self._lock:
            start_time = self._active_spans.pop(span_id, None)
            if start_time is None:
                return
            
            duration_ms = (time.time() - start_time) * 1000
            name = span_id.rsplit("_", 1)[0]
            self.registry.record(f"{name}_duration_ms", duration_ms)

    def record(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        self.registry.record(name, value, labels)

    def profile(self, name: str):
        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    span_id = self.start_span(name)
                    try:
                        return await func(*args, **kwargs)
                    finally:
                        self.end_span(span_id)
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    span_id = self.start_span(name)
                    try:
                        return func(*args, **kwargs)
                    finally:
                        self.end_span(span_id)
                return sync_wrapper
        return decorator

    def get_metrics(self) -> Dict[str, Dict[str, float]]:
        return self.registry.get_all_metrics()


class AdaptiveThrottler:
    def __init__(
        self,
        target_latency_ms: float = 100,
        min_rate: float = 1.0,
        max_rate: float = 100.0
    ):
        self.target_latency_ms = target_latency_ms
        self.min_rate = min_rate
        self.max_rate = max_rate
        self._current_rate = max_rate
        self._latency_samples: Deque[float] = deque(maxlen=100)
        self._lock = threading.RLock()

    def record_latency(self, latency_ms: float):
        with self._lock:
            self._latency_samples.append(latency_ms)
            self._adjust_rate()

    def _adjust_rate(self):
        if len(self._latency_samples) < 10:
            return
        
        avg_latency = sum(self._latency_samples) / len(self._latency_samples)
        
        if avg_latency > self.target_latency_ms * 1.5:
            self._current_rate = max(self.min_rate, self._current_rate * 0.8)
        elif avg_latency < self.target_latency_ms * 0.5:
            self._current_rate = min(self.max_rate, self._current_rate * 1.1)

    @property
    def current_rate(self) -> float:
        return self._current_rate

    async def wait(self):
        interval = 1.0 / self._current_rate
        await asyncio.sleep(interval)


class MemoryManager:
    def __init__(self, max_memory_mb: float = 512):
        self.max_memory_mb = max_memory_mb
        self._allocations: Dict[str, int] = {}
        self._lock = threading.RLock()

    def allocate(self, key: str, size_bytes: int) -> bool:
        with self._lock:
            current_usage = sum(self._allocations.values())
            max_bytes = self.max_memory_mb * 1024 * 1024
            
            if current_usage + size_bytes > max_bytes:
                return False
            
            self._allocations[key] = size_bytes
            return True

    def release(self, key: str) -> int:
        with self._lock:
            return self._allocations.pop(key, 0)

    def get_usage_mb(self) -> float:
        with self._lock:
            return sum(self._allocations.values()) / (1024 * 1024)

    def get_usage_percent(self) -> float:
        return (self.get_usage_mb() / self.max_memory_mb) * 100


class ConcurrencyLimiter:
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0
        self._lock = threading.RLock()

    async def acquire(self):
        await self._semaphore.acquire()
        with self._lock:
            self._active_count += 1

    def release(self):
        self._semaphore.release()
        with self._lock:
            self._active_count = max(0, self._active_count - 1)

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()

    @property
    def active_count(self) -> int:
        return self._active_count


class ConnectionPool(Generic[T]):
    def __init__(
        self,
        factory: Callable[[], Awaitable[T]],
        max_size: int = 10,
        min_size: int = 2
    ):
        self.factory = factory
        self.max_size = max_size
        self.min_size = min_size
        self._pool: asyncio.Queue[T] = asyncio.Queue(maxsize=max_size)
        self._size = 0
        self._lock = asyncio.Lock()

    async def initialize(self):
        async with self._lock:
            while self._size < self.min_size:
                conn = await self.factory()
                await self._pool.put(conn)
                self._size += 1

    async def acquire(self) -> T:
        async with self._lock:
            if self._pool.empty() and self._size < self.max_size:
                conn = await self.factory()
                self._size += 1
                return conn
        
        return await self._pool.get()

    async def release(self, conn: T):
        await self._pool.put(conn)

    async def __aenter__(self) -> T:
        return await self.acquire()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @property
    def available(self) -> int:
        return self._pool.qsize()


class BatchProcessor(Generic[T]):
    def __init__(
        self,
        processor: Callable[[List[T]], Awaitable[None]],
        batch_size: int = 10,
        max_wait_ms: float = 100
    ):
        self.processor = processor
        self.batch_size = batch_size
        self.max_wait_ms = max_wait_ms
        self._batch: List[T] = []
        self._last_process = time.time()
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None

    async def add(self, item: T):
        async with self._lock:
            self._batch.append(item)
            
            if len(self._batch) >= self.batch_size:
                await self._process()
            elif not self._task:
                self._task = asyncio.create_task(self._timer())

    async def _timer(self):
        await asyncio.sleep(self.max_wait_ms / 1000)
        async with self._lock:
            if self._batch:
                await self._process()
            self._task = None

    async def _process(self):
        if not self._batch:
            return
        
        batch = self._batch[:]
        self._batch = []
        self._last_process = time.time()
        
        try:
            await self.processor(batch)
        except Exception as e:
            logger.error(f"Batch processing error: {e}")

    async def flush(self):
        async with self._lock:
            await self._process()


@dataclass
class PerformanceReport:
    timestamp: float = field(default_factory=time.time)
    level: PerformanceLevel = PerformanceLevel.MEDIUM
    metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    memory_usage_mb: float = 0.0
    memory_usage_percent: float = 0.0
    active_connections: int = 0
    throughput_rps: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    error_rate_percent: float = 0.0
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level.value,
            "metrics": self.metrics,
            "memory": {
                "usage_mb": round(self.memory_usage_mb, 2),
                "usage_percent": round(self.memory_usage_percent, 2),
            },
            "connections": self.active_connections,
            "performance": {
                "throughput_rps": round(self.throughput_rps, 2),
                "avg_latency_ms": round(self.avg_latency_ms, 2),
                "p95_latency_ms": round(self.p95_latency_ms, 2),
                "p99_latency_ms": round(self.p99_latency_ms, 2),
                "error_rate_percent": round(self.error_rate_percent, 2),
            },
            "recommendations": self.recommendations,
        }


class PerformanceTuner:
    def __init__(self, config: Optional[PerformanceConfig] = None):
        self.capabilities = SystemCapabilities.detect()
        self.config = config or PerformanceConfig.from_capabilities(self.capabilities)
        
        self.profiler = PerformanceProfiler()
        self.throttler = AdaptiveThrottler()
        self.memory = MemoryManager(max_memory_mb=self.config.cache_size_mb)
        self.concurrency = ConcurrencyLimiter(max_concurrent=self.config.max_concurrent_requests)
        
        self._start_time = time.time()
        self._request_count = 0
        self._error_count = 0
        self._lock = threading.RLock()

    def record_request(self, latency_ms: float, success: bool = True):
        with self._lock:
            self._request_count += 1
            if not success:
                self._error_count += 1
        
        self.profiler.record("request_latency_ms", latency_ms)
        self.throttler.record_latency(latency_ms)

    async def execute_with_limits(
        self,
        func: Callable[[], Awaitable[T]]
    ) -> T:
        async with self.concurrency:
            await self.throttler.wait()
            start = time.time()
            try:
                result = await func()
                latency = (time.time() - start) * 1000
                self.record_request(latency, success=True)
                return result
            except Exception as e:
                latency = (time.time() - start) * 1000
                self.record_request(latency, success=False)
                raise

    def generate_report(self) -> PerformanceReport:
        elapsed = time.time() - self._start_time
        
        with self._lock:
            throughput = self._request_count / elapsed if elapsed > 0 else 0
            error_rate = (self._error_count / self._request_count * 100) if self._request_count > 0 else 0
        
        metrics = self.profiler.get_metrics()
        latency_metrics = metrics.get("request_latency_ms", {})
        
        recommendations = []
        
        if latency_metrics.get("p95", 0) > 500:
            recommendations.append("Consider reducing concurrent requests")
        
        memory_percent = self.memory.get_usage_percent()
        if memory_percent > 80:
            recommendations.append("Memory usage is high, consider increasing cache eviction")
        
        if error_rate > 5:
            recommendations.append("Error rate is elevated, review error logs")
        
        if throughput < 1:
            recommendations.append("Throughput is low, check for bottlenecks")
        
        return PerformanceReport(
            level=self.config.level,
            metrics=metrics,
            memory_usage_mb=self.memory.get_usage_mb(),
            memory_usage_percent=memory_percent,
            active_connections=self.concurrency.active_count,
            throughput_rps=throughput,
            avg_latency_ms=latency_metrics.get("avg", 0),
            p95_latency_ms=latency_metrics.get("p95", 0),
            p99_latency_ms=latency_metrics.get("p99", 0),
            error_rate_percent=error_rate,
            recommendations=recommendations
        )

    def optimize_config(self) -> PerformanceConfig:
        report = self.generate_report()
        
        if report.p95_latency_ms > 500:
            self.config.max_concurrent_requests = max(
                5,
                int(self.config.max_concurrent_requests * 0.8)
            )
        
        if report.memory_usage_percent > 80:
            self.config.cache_size_mb = self.config.cache_size_mb * 0.8
        
        if report.throughput_rps > 50 and report.p95_latency_ms < 100:
            self.config.max_concurrent_requests = min(
                50,
                int(self.config.max_concurrent_requests * 1.2)
            )
        
        return self.config


def detect_system_capabilities() -> SystemCapabilities:
    return SystemCapabilities.detect()


def create_performance_config(
    level: Optional[PerformanceLevel] = None
) -> PerformanceConfig:
    if level:
        return PerformanceConfig(level=level)
    
    caps = detect_system_capabilities()
    return PerformanceConfig.from_capabilities(caps)


def create_performance_tuner(
    config: Optional[PerformanceConfig] = None
) -> PerformanceTuner:
    return PerformanceTuner(config)


def create_profiler() -> PerformanceProfiler:
    return PerformanceProfiler()


def create_batch_processor(
    processor: Callable[[List[T]], Awaitable[None]],
    batch_size: int = 10
) -> BatchProcessor[T]:
    return BatchProcessor(processor, batch_size=batch_size)


class PerformanceOptimizationSuite:
    def __init__(self):
        self.capabilities = detect_system_capabilities()
        self.config = create_performance_config()
        self.tuner = create_performance_tuner(self.config)
        self.profiler = self.tuner.profiler

    def profile(self, name: str):
        return self.profiler.profile(name)

    async def execute(self, func: Callable[[], Awaitable[T]]) -> T:
        return await self.tuner.execute_with_limits(func)

    def record(self, name: str, value: float):
        self.profiler.record(name, value)

    def get_report(self) -> PerformanceReport:
        return self.tuner.generate_report()

    def optimize(self) -> PerformanceConfig:
        return self.tuner.optimize_config()


def create_optimization_suite() -> PerformanceOptimizationSuite:
    return PerformanceOptimizationSuite()
