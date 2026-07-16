"""Health endpoint smoke tests for Phase 0 placeholder API."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "enterprise-rag-platform-api"


def test_ready_ok() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
