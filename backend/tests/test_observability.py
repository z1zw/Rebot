from __future__ import annotations

import importlib
import sys
import types

from fastapi import APIRouter
from fastapi.testclient import TestClient

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


def _prepare_main_module():
    for module_name in _ROUTER_MODULES:
        module = types.ModuleType(module_name)
        router = APIRouter()
        if module_name == "app.api.router_executions":
            @router.get("/executions")
            async def _executions():
                return {"ok": True}
        module.router = router
        sys.modules[module_name] = module
    import app.main as main_module

    return importlib.reload(main_module)


def _make_client(monkeypatch, *, mode: str, expected_key: str | None):
    main_module = _prepare_main_module()
    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(main_module, "init_sentry", lambda: None)
    monkeypatch.setattr(main_module.settings, "auth_mode", mode)
    monkeypatch.setattr(main_module.settings, "server_api_key", expected_key)
    return TestClient(main_module.app)


def test_metrics_endpoint_not_guarded_by_auth(monkeypatch):
    client = _make_client(monkeypatch, mode="enforce", expected_key="k1")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "rebot_metrics_available" in resp.text
    assert resp.headers.get("content-type", "").startswith("text/plain")


def test_auth_still_enforced_after_observability(monkeypatch):
    client = _make_client(monkeypatch, mode="enforce", expected_key="k1")
    blocked = client.get("/api/executions")
    assert blocked.status_code == 401
    allowed = client.get("/api/executions", headers={"x-api-key": "k1"})
    assert allowed.status_code == 200
