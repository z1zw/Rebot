from __future__ import annotations

import re
from typing import Any

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

    _PROMETHEUS_AVAILABLE = True
except Exception:
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    _PROMETHEUS_AVAILABLE = False

    class _NoopMetric:
        def labels(self, **_: Any) -> "_NoopMetric":
            return self

        def inc(self, *_: Any, **__: Any) -> None:
            return None

        def observe(self, *_: Any, **__: Any) -> None:
            return None

    def Counter(*_: Any, **__: Any) -> _NoopMetric:
        return _NoopMetric()

    def Histogram(*_: Any, **__: Any) -> _NoopMetric:
        return _NoopMetric()

    def generate_latest() -> bytes:
        return b""


_HTTP_REQUESTS_TOTAL = Counter(
    "rebot_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

_HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "rebot_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path", "status"],
)

_OPERATION_TOTAL = Counter(
    "rebot_operation_total",
    "Total operation outcomes",
    ["operation", "status"],
)

_OPERATION_DURATION_SECONDS = Histogram(
    "rebot_operation_duration_seconds",
    "Operation latency in seconds",
    ["operation", "status"],
)

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
_LONG_NUM_RE = re.compile(r"(?<=/)\d{3,}(?=/|$)")


def _normalize_path(path: str) -> str:
    out = _UUID_RE.sub("{id}", path or "/")
    out = _LONG_NUM_RE.sub("{id}", out)
    out = re.sub(r"/run/[A-Za-z0-9_-]+", "/run/{id}", out)
    return out


def observe_http_request(method: str, path: str, status_code: int, elapsed_seconds: float) -> None:
    labels = {
        "method": (method or "GET").upper(),
        "path": _normalize_path(path),
        "status": str(int(status_code)),
    }
    _HTTP_REQUESTS_TOTAL.labels(**labels).inc()
    _HTTP_REQUEST_DURATION_SECONDS.labels(**labels).observe(max(0.0, float(elapsed_seconds)))


def observe_operation(operation: str, status: str, elapsed_seconds: float | None = None) -> None:
    labels = {
        "operation": operation or "unknown",
        "status": status or "unknown",
    }
    _OPERATION_TOTAL.labels(**labels).inc()
    if elapsed_seconds is not None:
        _OPERATION_DURATION_SECONDS.labels(**labels).observe(max(0.0, float(elapsed_seconds)))


def render_metrics() -> bytes:
    header = f"rebot_metrics_available {1 if _PROMETHEUS_AVAILABLE else 0}\n".encode("utf-8")
    return header + generate_latest()


def metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST
