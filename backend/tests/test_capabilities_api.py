from fastapi.testclient import TestClient

from app.main import app


def test_capabilities_providers_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/api/capabilities/providers")
    assert resp.status_code == 200
    body = resp.json()
    assert "providers" in body
    assert isinstance(body["providers"], list)
    assert body["count"] >= 1


def test_capabilities_tools_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/api/capabilities/tools")
    assert resp.status_code == 200
    body = resp.json()
    assert "tools" in body
    assert isinstance(body["tools"], list)
    assert body["count"] >= 1


def test_capabilities_resources_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/api/capabilities/resources")
    assert resp.status_code == 200
    body = resp.json()
    assert "resources" in body
    resources = body["resources"]
    assert "max_model_concurrency" in resources
    assert "max_split_concurrency" in resources
