from __future__ import annotations

import os

from app.core.logging import get_logger

logger = get_logger(__name__)
_INITIALIZED = False


def init_tracing(service_name: str = "rebot-backend", app=None) -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    except Exception:
        logger.info("tracing_disabled", extra={"event": "tracing_disabled", "reason": "missing_opentelemetry"})
        _INITIALIZED = True
        return

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    exporter = None

    endpoint = (os.getenv("REBOT_OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip()
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=endpoint)
        except Exception:
            exporter = None

    if exporter is None:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
        except Exception:
            pass

    logger.info("tracing_enabled", extra={"event": "tracing_enabled", "otlp_endpoint": endpoint or "console"})
    _INITIALIZED = True
