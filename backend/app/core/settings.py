from __future__ import annotations

import os
from pathlib import Path


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file()


class Settings:
    redis_url: str | None = os.getenv("REDIS_URL")
    rabbitmq_url: str | None = os.getenv("RABBITMQ_URL")
    force_local_tasks: bool = os.getenv("FORCE_LOCAL_TASKS", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    embed_worker: bool = os.getenv("EMBED_WORKER", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    database_url: str | None = os.getenv("DATABASE_URL")
    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_anon_key: str | None = os.getenv("SUPABASE_ANON_KEY")
    supabase_service_key: str | None = os.getenv("SUPABASE_SERVICE_KEY")
    sentry_dsn: str | None = os.getenv("SENTRY_DSN")
    launchdarkly_sdk_key: str | None = os.getenv("LAUNCHDARKLY_SDK_KEY")
    clamav_host: str | None = os.getenv("CLAMAV_HOST")
    clamav_port: int | None = int(os.getenv("CLAMAV_PORT", "3310"))
    cors_allow_origins: list[str] = [
        x.strip()
        for x in os.getenv(
            "CORS_ALLOW_ORIGINS",
            "http://localhost,http://127.0.0.1,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if x.strip()
    ]
    auth_mode: str = os.getenv("REBOT_AUTH_MODE", "off").strip().lower()
    server_api_key: str | None = os.getenv("REBOT_SERVER_API_KEY")
    model_max_concurrency_default: int = int(os.getenv("REBOT_MODEL_MAX_CONCURRENCY_DEFAULT", "3"))
    split_max_concurrency_default: int = int(os.getenv("REBOT_SPLIT_MAX_CONCURRENCY_DEFAULT", "2"))
    tracing_enabled: bool = os.getenv("REBOT_TRACING_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


settings = Settings()
