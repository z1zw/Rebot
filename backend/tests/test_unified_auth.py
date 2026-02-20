from __future__ import annotations

import sys
import types

from fastapi import APIRouter
from fastapi.testclient import TestClient
from fastapi import WebSocket

from app.core.auth import evaluate_api_key, extract_api_key_from_headers
from app.core.settings import settings

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


def _make_client(monkeypatch, *, mode: str, expected_key: str | None):
    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(main_module, "init_sentry", lambda: None)
    monkeypatch.setattr(main_module.settings, "auth_mode", mode)
    monkeypatch.setattr(main_module.settings, "server_api_key", expected_key)
    return TestClient(main_module.app)


def test_enforce_mode_blocks_missing_http_key(monkeypatch):
    client = _make_client(monkeypatch, mode="enforce", expected_key="k1")
    resp = client.get("/api/executions")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "unauthorized"


def test_enforce_mode_allows_valid_http_key_header(monkeypatch):
    client = _make_client(monkeypatch, mode="enforce", expected_key="k1")
    resp = client.get("/api/executions", headers={"x-api-key": "k1"})
    assert resp.status_code == 200
    assert "executions" in resp.json()


def test_enforce_mode_allows_valid_http_key_query(monkeypatch):
    client = _make_client(monkeypatch, mode="enforce", expected_key="k1")
    resp = client.get("/api/executions?api_key=k1")
    assert resp.status_code == 200
    assert "executions" in resp.json()


def test_compat_mode_allows_missing_but_rejects_invalid_http_key(monkeypatch):
    client = _make_client(monkeypatch, mode="compat", expected_key="k1")

    missing = client.get("/api/executions")
    assert missing.status_code == 200

    invalid = client.get("/api/executions", headers={"x-api-key": "bad"})
    assert invalid.status_code == 401
    assert invalid.json()["detail"] == "invalid_api_key"


def test_non_api_path_not_guarded_by_http_middleware(monkeypatch):
    client = _make_client(monkeypatch, mode="enforce", expected_key="k1")
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_enforce_mode_blocks_missing_ws_key(monkeypatch):
    client = _make_client(monkeypatch, mode="enforce", expected_key="k1")
    with client.websocket_connect("/ws/events") as ws:
        data = ws.receive()
    assert data["type"] == "websocket.close"
    assert data["code"] == 4401


def test_enforce_mode_allows_valid_ws_key(monkeypatch):
    client = _make_client(monkeypatch, mode="enforce", expected_key="k1")
    with client.websocket_connect("/ws/events?api_key=k1") as ws:
        assert ws is not None
