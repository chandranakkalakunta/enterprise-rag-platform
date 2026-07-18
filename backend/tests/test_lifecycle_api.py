"""API tests for publish / retire endpoints (Phase 2.4)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.services.lifecycle import LifecycleResult
from app.services.lifecycle_rules import ConflictError, InvalidIdError, NotFoundError


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AUTH_DEV_BYPASS", "true")
    get_settings.cache_clear()
    return TestClient(app)


NOW = datetime(2026, 7, 17, 15, 0, 0, tzinfo=timezone.utc)


def test_publish_ready_success(client: TestClient) -> None:
    result = LifecycleResult(
        document_id="doc-1",
        version_id="ver-1",
        status="published",
        active_version_id="ver-1",
        published_at=NOW,
        published_by="dev-bypass",
        previous_published_version_id=None,
    )
    with (
        patch("app.api.v1.documents.firestore.Client", return_value=MagicMock()),
        patch("app.api.v1.documents.publish_version", return_value=result) as pub,
        patch("google.cloud.storage.Client", return_value=MagicMock()),
        patch(
            "app.services.vector_ops.activate_version_vectors",
            return_value="activated",
        ) as act,
    ):
        response = client.post("/api/v1/documents/doc-1/versions/ver-1/publish")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "published"
    assert body["document_id"] == "doc-1"
    assert body["version_id"] == "ver-1"
    assert body["active_version_id"] == "ver-1"
    assert body["published_by"] == "dev-bypass"
    assert body["previous_published_version_id"] is None
    pub.assert_called_once()
    act.assert_called_once()
    kwargs = pub.call_args.kwargs
    assert kwargs["document_id"] == "doc-1"
    assert kwargs["version_id"] == "ver-1"
    assert kwargs["actor"] == "dev-bypass"


def test_publish_supersedes_previous(client: TestClient) -> None:
    result = LifecycleResult(
        document_id="doc-1",
        version_id="ver-2",
        status="published",
        active_version_id="ver-2",
        published_at=NOW,
        published_by="dev-bypass",
        previous_published_version_id="ver-1",
    )
    with (
        patch("app.api.v1.documents.firestore.Client", return_value=MagicMock()),
        patch("app.api.v1.documents.publish_version", return_value=result),
        patch("google.cloud.storage.Client", return_value=MagicMock()),
        patch(
            "app.services.vector_ops.activate_version_vectors",
            return_value="activated",
        ) as act,
        patch(
            "app.services.vector_ops.deactivate_version_vectors",
            return_value="deactivated",
        ) as deact,
    ):
        body = client.post("/api/v1/documents/doc-1/versions/ver-2/publish").json()

    assert body["status"] == "published"
    assert body["previous_published_version_id"] == "ver-1"
    assert body["active_version_id"] == "ver-2"
    act.assert_called_once()
    deact.assert_called_once()
    assert deact.call_args.kwargs["version_id"] == "ver-1"


def test_retire_published_clears_pointer(client: TestClient) -> None:
    result = LifecycleResult(
        document_id="doc-1",
        version_id="ver-1",
        status="retired",
        active_version_id=None,
        retired_at=NOW,
        retired_by="dev-bypass",
        cleared_active_pointer=True,
    )
    with (
        patch("app.api.v1.documents.firestore.Client", return_value=MagicMock()),
        patch("app.api.v1.documents.retire_version", return_value=result),
        patch("google.cloud.storage.Client", return_value=MagicMock()),
        patch(
            "app.services.vector_ops.deactivate_version_vectors",
            return_value="deactivated",
        ) as deact,
    ):
        response = client.post("/api/v1/documents/doc-1/versions/ver-1/retire")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "retired"
    assert body["active_version_id"] is None
    assert body["cleared_active_pointer"] is True
    assert body["retired_by"] == "dev-bypass"
    deact.assert_called_once()


def test_publish_illegal_transition_409(client: TestClient) -> None:
    with (
        patch("app.api.v1.documents.firestore.Client", return_value=MagicMock()),
        patch(
            "app.api.v1.documents.publish_version",
            side_effect=ConflictError(
                "Cannot publish version in status 'processing' (allowed: ready)"
            ),
        ),
    ):
        response = client.post("/api/v1/documents/doc-1/versions/ver-1/publish")

    assert response.status_code == 409
    assert "Cannot publish" in response.json()["detail"]


def test_retire_illegal_transition_409(client: TestClient) -> None:
    with (
        patch("app.api.v1.documents.firestore.Client", return_value=MagicMock()),
        patch(
            "app.api.v1.documents.retire_version",
            side_effect=ConflictError(
                "Cannot retire version in status 'failed' (allowed: published, ready)"
            ),
        ),
    ):
        response = client.post("/api/v1/documents/doc-1/versions/ver-1/retire")

    assert response.status_code == 409
    assert "Cannot retire" in response.json()["detail"]


def test_publish_not_found_404(client: TestClient) -> None:
    with (
        patch("app.api.v1.documents.firestore.Client", return_value=MagicMock()),
        patch(
            "app.api.v1.documents.publish_version",
            side_effect=NotFoundError("Document not found: missing"),
        ),
    ):
        response = client.post("/api/v1/documents/missing/versions/ver-1/publish")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_retire_version_not_found_404(client: TestClient) -> None:
    with (
        patch("app.api.v1.documents.firestore.Client", return_value=MagicMock()),
        patch(
            "app.api.v1.documents.retire_version",
            side_effect=NotFoundError("Version not found: v-x under document d1"),
        ),
    ):
        response = client.post("/api/v1/documents/d1/versions/v-x/retire")

    assert response.status_code == 404


def test_publish_invalid_id_400(client: TestClient) -> None:
    with (
        patch("app.api.v1.documents.firestore.Client", return_value=MagicMock()),
        patch(
            "app.api.v1.documents.publish_version",
            side_effect=InvalidIdError("document_id contains invalid characters"),
        ),
    ):
        # Path may still route; service validates
        response = client.post("/api/v1/documents/bad/versions/ver/publish")

    assert response.status_code == 400


def test_publish_requires_auth_when_bypass_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_DEV_BYPASS", "false")
    monkeypatch.setenv("UPLOAD_BEARER_TOKEN", "secret")
    get_settings.cache_clear()
    local = TestClient(app)

    denied = local.post("/api/v1/documents/d1/versions/v1/publish")
    assert denied.status_code == 401

    result = LifecycleResult(
        document_id="d1",
        version_id="v1",
        status="published",
        active_version_id="v1",
        published_at=NOW,
        published_by="bearer-token",
    )
    with (
        patch("app.api.v1.documents.firestore.Client", return_value=MagicMock()),
        patch("app.api.v1.documents.publish_version", return_value=result) as pub,
        patch("google.cloud.storage.Client", return_value=MagicMock()),
        patch(
            "app.services.vector_ops.activate_version_vectors",
            return_value="skipped",
        ),
    ):
        ok = local.post(
            "/api/v1/documents/d1/versions/v1/publish",
            headers={"Authorization": "Bearer secret"},
        )
    assert ok.status_code == 200
    assert pub.call_args.kwargs["actor"] == "bearer-token"
