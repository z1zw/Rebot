"""Model configuration."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ModelConfig:
    api_key: str
    model: str
    base_url: str | None = None
    timeout_s: float = 60.0
    max_retries: int = 4
    max_concurrency: int = 2
    min_request_interval_s: float = 0.15
    retry_base_s: float = 0.8
    retry_cap_s: float = 30.0
    extra_headers: dict[str, str] | None = None

    @classmethod
    def from_env(
        cls,
        *,
        model: str,
        api_key_env: str,
        base_url_env: str | None = None,
        default_base_url: str | None = None,
    ) -> "ModelConfig":
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(f"Missing API key env: {api_key_env}")
        base_url = os.environ.get(base_url_env) if base_url_env else None
        if base_url is None:
            base_url = default_base_url
        return cls(api_key=api_key, model=model, base_url=base_url)
