import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.rest import router as rest_router
from app.api.router_devserver import router as devserver_router
from app.api.router_emulator import router as emulator_router
from app.api.router_executions import router as executions_router
from app.api.router_files import router as files_router
from app.api.router_intel import router as intel_router
from app.api.router_security import router as security_router
from app.api.router_capabilities import router as capabilities_router
from app.api.router_git import router as git_router
from app.api.ws import router as ws_router
from app.core.db import init_db
from app.core.sentry import init_sentry
from app.core.flags import flags
from app.core.auth import evaluate_api_key, extract_api_key_from_headers
from app.core.logging import get_logger, setup_structured_logging
from app.core.metrics import metrics_content_type, observe_http_request, render_metrics
from app.core.settings import settings
from app.core.tracing import init_tracing

setup_structured_logging()
logger = get_logger(__name__)
app = FastAPI(title="Rebot Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins or ["http://localhost", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router, prefix="/api")
app.include_router(rest_router)
app.include_router(devserver_router, prefix="/api")
app.include_router(devserver_router)
app.include_router(executions_router, prefix="/api")
app.include_router(executions_router)
app.include_router(files_router, prefix="/api")
app.include_router(files_router)
app.include_router(intel_router, prefix="/api")
app.include_router(intel_router)
app.include_router(emulator_router, prefix="/api")
app.include_router(emulator_router)
app.include_router(security_router, prefix="/api")
app.include_router(security_router)
app.include_router(capabilities_router, prefix="/api")
app.include_router(capabilities_router)
app.include_router(git_router, prefix="/api")
app.include_router(git_router)
app.include_router(ws_router, prefix="/ws")
_worker_task = None


@app.middleware("http")
async def unified_auth_guard(request: Request, call_next):
    started_at = time.perf_counter()
    status_code = 500
    path = request.url.path
    mode = settings.auth_mode
    expected = settings.server_api_key or ""
    is_protected = path.startswith("/api/") or path.startswith("/ws/")
    try:
        if is_protected:
            provided = extract_api_key_from_headers(request.headers)
            if not provided:
                provided = (request.query_params.get("api_key") or "").strip()
            decision = evaluate_api_key(mode=mode, expected=expected, provided=provided)
            if not decision.allowed:
                status_code = 401
                return JSONResponse(status_code=401, content={"detail": decision.reason})
        response = await call_next(request)
        status_code = int(response.status_code)
        return response
    finally:
        observe_http_request(
            method=request.method,
            path=path,
            status_code=status_code,
            elapsed_seconds=time.perf_counter() - started_at,
        )


@app.on_event("startup")
async def on_startup():
    global _worker_task
    init_db()
    init_sentry()
    init_tracing(app=app)
    _ = flags
    logger.info(
        "backend_startup",
        extra={"event": "backend_startup", "auth_mode": settings.auth_mode, "embed_worker": settings.embed_worker},
    )
    if settings.rabbitmq_url and not settings.force_local_tasks and settings.embed_worker:
        # Run queue consumer in-process so desktop mode does not require extra terminal commands.
        import asyncio
        from app.worker import run_worker

        _worker_task = asyncio.create_task(run_worker())


@app.on_event("shutdown")
async def on_shutdown():
    global _worker_task
    if _worker_task is not None:
        _worker_task.cancel()
        _worker_task = None
    logger.info("backend_shutdown", extra={"event": "backend_shutdown"})


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    return Response(content=render_metrics(), headers={"Content-Type": metrics_content_type()})

