from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import random
import time
from typing import Iterable

import httpx


def parse_retry_after_seconds(raw: str | None) -> float | None:
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    try:
        return max(0.0, float(text))
    except Exception:
        pass
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0.0, (dt - now).total_seconds())
    except Exception:
        return None


def compute_backoff_seconds(
    attempt: int,
    *,
    retry_after_s: float | None = None,
    base_s: float = 1.0,
    cap_s: float = 30.0,
    jitter_s: float = 0.35,
) -> float:
    if retry_after_s is not None and retry_after_s >= 0:
        return retry_after_s
    exp = min(cap_s, base_s * (2 ** max(0, attempt)))
    return max(0.0, exp + random.uniform(0.0, jitter_s))


def sleep_backoff(delay_s: float) -> None:
    if delay_s > 0:
        time.sleep(delay_s)


DEFAULT_RETRYABLE_HTTP_STATUS: tuple[int, ...] = (429, 500, 502, 503, 504)


def is_retryable_status(
    status_code: int | None, retryable: Iterable[int] = DEFAULT_RETRYABLE_HTTP_STATUS
) -> bool:
    return status_code in set(retryable)


def is_retryable_exception(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code if exc.response is not None else None
        return is_retryable_status(status)
    return False


def next_retry_delay_seconds(
    *,
    attempt: int,
    response_headers: dict | None,
    base_s: float,
    cap_s: float,
) -> float:
    retry_after_s = None
    if response_headers:
        retry_after_s = parse_retry_after_seconds(response_headers.get("Retry-After"))
    return compute_backoff_seconds(
        attempt,
        retry_after_s=retry_after_s,
        base_s=base_s,
        cap_s=cap_s,
    )
