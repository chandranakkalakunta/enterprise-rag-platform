"""Health and readiness endpoint tests (Phase 1.5)."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "rag-api"
    assert "version" in body
    assert "deployed_at" in body
    assert isinstance(body["version"], str)
    assert isinstance(body["deployed_at"], str)


def test_ready_ok() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["service"] == "rag-api"
    assert "version" in body
    assert "deployed_at" in body
    assert "checks" in body
    assert isinstance(body["checks"], dict)


def test_health_respects_env_version_and_deployed_at(monkeypatch) -> None:
    monkeypatch.setenv("APP_VERSION", "1.5.0-test")
    monkeypatch.setenv("DEPLOYED_AT", "2026-07-17T12:00:00Z")
    # Reload module env reads happen at request time — re-import not needed
    # if helpers read getenv on each call
    from importlib import reload

    import app.main as main_mod

    reload(main_mod)
    local_client = TestClient(main_mod.app)

    body = local_client.get("/health").json()
    assert body["version"] == "1.5.0-test"
    assert body["deployed_at"] == "2026-07-17T12:00:00Z"

    ready = local_client.get("/ready").json()
    assert ready["version"] == "1.5.0-test"
    assert ready["deployed_at"] == "2026-07-17T12:00:00Z"


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
