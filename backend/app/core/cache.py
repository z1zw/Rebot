from __future__ import annotations

import json
from typing import Any

from app.core.settings import settings


class Cache:
    def __init__(self) -> None:
        self._memory: dict[str, Any] = {}
        self._redis = None
        if settings.redis_url:
            import redis

            self._redis = redis.from_url(settings.redis_url, decode_responses=True)

    def get(self, key: str) -> dict[str, Any] | None:
        if self._redis:
            try:
                raw = self._redis.get(key)
                return json.loads(raw) if raw else None
            except Exception:
                # Redis is optional at runtime; degrade to local cache instead of failing requests.
                self._redis = None
                return self._memory.get(key)
        return self._memory.get(key)

    def set(self, key: str, value: dict[str, Any], ttl_s: int | None = None) -> None:
        if self._redis:
            try:
                if ttl_s:
                    self._redis.setex(key, ttl_s, json.dumps(value))
                else:
                    self._redis.set(key, json.dumps(value))
                return
            except Exception:
                self._redis = None
        else:
            self._memory[key] = value
            return
        self._memory[key] = value


cache = Cache()
