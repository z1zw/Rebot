from __future__ import annotations

import sys
import types
from pathlib import Path

from fastapi import APIRouter
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_ROUTER_MODULES = [
    "app.api.rest",
    "app.api.router_devserver",
    "app.api.router_emulator",
    "app.api.router_executions",
    "app.api.router_files",
    "app.api.router_intel",
    "app.api.router_security",
    "app.api.ws",
]
for module_name in _ROUTER_MODULES:
    module = types.ModuleType(module_name)
    router = APIRouter()
    if module_name == "app.api.router_executions":
        @router.get("/executions")
        async def _executions():
            return {"ok": True}
    if module_name == "app.api.ws":
        from fastapi import WebSocket
        from app.core.auth import evaluate_api_key, extract_api_key_from_headers
        from app.core.settings import settings

        @router.websocket("/events")
        async def _events(ws: WebSocket):
            provided = extract_api_key_from_headers(ws.headers)
            if not provided:
                provided = (ws.query_params.get("api_key") or "").strip()
            decision = evaluate_api_key(
                mode=settings.auth_mode,
                expected=settings.server_api_key or "",
                provided=provided,
            )
            if not decision.allowed:
                await ws.close(code=4401, reason=decision.reason)
                return
            await ws.accept()
            await ws.close(code=1000)
    module.router = router
    sys.modules[module_name] = module

import app.main as main_module


def _client(*, mode: str, expected_key: str | None) -> TestClient:
    main_module.init_db = lambda: None
    main_module.init_sentry = lambda: None
    main_module.settings.auth_mode = mode
    main_module.settings.server_api_key = expected_key
    return TestClient(main_module.app)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def run() -> None:
    c = _client(mode="enforce", expected_key="k1")

    r = c.get("/api/executions")
    _assert(r.status_code == 401, f"expected 401, got {r.status_code}")
    _assert(r.json().get("detail") == "unauthorized", f"unexpected detail: {r.text}")

    r = c.get("/api/executions", headers={"x-api-key": "k1"})
    _assert(r.status_code == 200, f"expected 200 with x-api-key, got {r.status_code}")

    r = c.get("/api/executions?api_key=k1")
    _assert(r.status_code == 200, f"expected 200 with query api_key, got {r.status_code}")

    r = c.get("/docs")
    _assert(r.status_code == 200, f"expected /docs bypass, got {r.status_code}")

    try:
        with c.websocket_connect("/ws/events"):
            raise AssertionError("ws should not connect without key")
    except WebSocketDisconnect as exc:
        _assert(exc.code == 4401, f"expected ws 4401, got {exc.code}")

    with c.websocket_connect("/ws/events?api_key=k1"):
        pass

    c = _client(mode="compat", expected_key="k1")
    _assert(c.get("/api/executions").status_code == 200, "compat should allow missing key")
    r = c.get("/api/executions", headers={"x-api-key": "bad"})
    _assert(r.status_code == 401, f"compat invalid should be 401, got {r.status_code}")
    _assert(r.json().get("detail") == "invalid_api_key", f"unexpected compat detail: {r.text}")

    c = _client(mode="off", expected_key="k1")
    _assert(c.get("/api/executions").status_code == 200, "off should allow")
    with c.websocket_connect("/ws/events"):
        pass


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"[FAIL] auth smoke failed: {exc}")
        sys.exit(1)
    print("[OK] auth smoke passed")
