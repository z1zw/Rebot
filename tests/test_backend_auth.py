from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from backend.app import main as backend_main
from app.core.auth import evaluate_api_key
from app.core.settings import settings


@pytest.mark.parametrize(
    ("mode", "provided", "expected_allowed", "expected_reason"),
    [
        ("off", "", True, "off"),
        ("compat", "", True, "compat_allow"),
        ("compat", "wrong", False, "invalid_api_key"),
        ("compat", "secret", True, "compat_allow"),
        ("enforce", "", False, "unauthorized"),
        ("enforce", "wrong", False, "unauthorized"),
        ("enforce", "secret", True, "enforce_allow"),
    ],
)
def test_evaluate_api_key_modes(
    mode: str,
    provided: str,
    expected_allowed: bool,
    expected_reason: str,
):
    decision = evaluate_api_key(mode=mode, expected="secret", provided=provided)
    assert decision.allowed is expected_allowed
    assert decision.reason == expected_reason


def test_http_auth_modes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "server_api_key", "secret", raising=False)
    endpoint = "/api/executions?limit=1"

    with TestClient(backend_main.app) as client:
        monkeypatch.setattr(settings, "auth_mode", "off", raising=False)
        r = client.get(endpoint)
        assert r.status_code == 200

        monkeypatch.setattr(settings, "auth_mode", "compat", raising=False)
        r = client.get(endpoint)
        assert r.status_code == 200

        r = client.get(endpoint, headers={"X-API-Key": "wrong"})
        assert r.status_code == 401
        assert r.json().get("detail") == "invalid_api_key"

        r = client.get(endpoint, headers={"X-API-Key": "secret"})
        assert r.status_code == 200

        monkeypatch.setattr(settings, "auth_mode", "enforce", raising=False)
        r = client.get(endpoint)
        assert r.status_code == 401
        assert r.json().get("detail") == "unauthorized"

        r = client.get(endpoint, headers={"Authorization": "Bearer secret"})
        assert r.status_code == 200


def test_ws_events_auth_enforce_rejects_without_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "auth_mode", "enforce", raising=False)
    monkeypatch.setattr(settings, "server_api_key", "secret", raising=False)

    with TestClient(backend_main.app) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/ws/events"):
                pass
        assert exc.value.code == 4401


def test_ws_events_auth_enforce_accepts_with_key(monkeypatch: pytest.MonkeyPatch):
    class FakeBus:
        async def next(self):
            return {"run_id": "run-1", "events": [{"type": "console_log", "payload": {"text": "ok"}}]}

    monkeypatch.setattr(settings, "auth_mode", "enforce", raising=False)
    monkeypatch.setattr(settings, "server_api_key", "secret", raising=False)
    monkeypatch.setattr("backend.app.api.ws.get_event_bus", lambda: FakeBus())

    with TestClient(backend_main.app) as client:
        with client.websocket_connect("/ws/events", headers={"X-API-Key": "secret"}) as ws:
            data = ws.receive_json()
            assert data["run_id"] == "run-1"
            assert data["events"][0]["type"] == "console_log"
