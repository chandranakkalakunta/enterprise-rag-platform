"""Phase 5.3 — document list/get Admin APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.firestore_repo import get_document, list_documents, version_summary_from_data


@pytest.fixture(autouse=True)
def _clear_settings() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AUTH_DEV_BYPASS", "true")
    get_settings.cache_clear()
    return TestClient(app)


NOW = datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc)


def test_version_summary_from_data() -> None:
    s = version_summary_from_data(
        "v1",
        {
            "status": "ready",
            "filename": "a.md",
            "gcs_uri": "gs://b/raw/d/v1/a.md",
            "created_at": NOW,
            "chunk_count": 3,
            "embeddings_status": "ready",
        },
    )
    assert s["version_id"] == "v1"
    assert s["status"] == "ready"
    assert s["filename"] == "a.md"
    assert s["chunk_count"] == 3


def test_get_document_missing() -> None:
    client = MagicMock()
    snap = MagicMock()
    snap.exists = False
    client.collection.return_value.document.return_value.get.return_value = snap
    assert get_document(client, "missing") is None


def test_get_document_with_versions() -> None:
    fs = MagicMock()
    doc_snap = MagicMock()
    doc_snap.exists = True
    doc_snap.to_dict.return_value = {
        "title": "Policy",
        "collection": "policies",
        "active_version_id": "v2",
        "latest_version_id": "v2",
        "created_by": "admin@gmail.com",
        "created_at": NOW,
        "updated_at": NOW,
    }
    doc_ref = MagicMock()
    fs.collection.return_value.document.return_value = doc_ref
    doc_ref.get.return_value = doc_snap

    v1 = MagicMock()
    v1.id = "v1"
    v1.to_dict.return_value = {
        "status": "retired",
        "filename": "a.md",
        "created_at": NOW,
    }
    v2 = MagicMock()
    v2.id = "v2"
    v2.to_dict.return_value = {
        "status": "published",
        "filename": "a.md",
        "created_at": NOW,
    }
    doc_ref.collection.return_value.stream.return_value = [v1, v2]

    out = get_document(fs, "doc-1", include_versions=True)
    assert out is not None
    assert out["document_id"] == "doc-1"
    assert out["title"] == "Policy"
    assert len(out["versions"]) == 2
    assert out["latest_version"]["version_id"] == "v2"
    assert out["latest_version"]["status"] == "published"


def test_list_documents_api(client: TestClient) -> None:
    rows = [
        {
            "document_id": "d1",
            "title": "T1",
            "collection": None,
            "active_version_id": "v1",
            "latest_version_id": "v1",
            "created_at": NOW,
            "updated_at": NOW,
            "created_by": "a@b.com",
            "latest_version": {
                "version_id": "v1",
                "status": "ready",
                "filename": "x.md",
                "gcs_uri": "gs://b/x",
                "content_type": "text/markdown",
                "size_bytes": 10,
                "created_at": NOW,
                "created_by": "a@b.com",
                "chunk_count": 1,
                "embeddings_status": "ready",
                "vector_status": "upserted",
                "error_message": None,
                "text_preview": "hi",
            },
        }
    ]
    with patch("app.api.v1.documents.firestore.Client", return_value=MagicMock()), patch(
        "app.api.v1.documents.list_documents", return_value=rows
    ):
        res = client.get("/api/v1/documents")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 1
    assert body["documents"][0]["document_id"] == "d1"
    assert body["documents"][0]["latest_version"]["status"] == "ready"


def test_get_document_api_404(client: TestClient) -> None:
    with patch("app.api.v1.documents.firestore.Client", return_value=MagicMock()), patch(
        "app.api.v1.documents.get_document", return_value=None
    ):
        res = client.get("/api/v1/documents/missing-id")
    assert res.status_code == 404


def test_get_document_api_ok(client: TestClient) -> None:
    raw = {
        "document_id": "d1",
        "title": "T",
        "collection": "c",
        "active_version_id": None,
        "latest_version_id": "v1",
        "created_at": NOW,
        "updated_at": NOW,
        "created_by": "a@b.com",
        "latest_version": {
            "version_id": "v1",
            "status": "ready",
            "filename": "a.md",
            "gcs_uri": "gs://b/a",
            "content_type": "text/markdown",
            "size_bytes": 1,
            "created_at": NOW,
            "created_by": "a@b.com",
            "chunk_count": 2,
            "embeddings_status": "ready",
            "vector_status": None,
            "error_message": None,
            "text_preview": None,
        },
        "versions": [
            {
                "version_id": "v1",
                "status": "ready",
                "filename": "a.md",
                "gcs_uri": "gs://b/a",
                "content_type": "text/markdown",
                "size_bytes": 1,
                "created_at": NOW,
                "created_by": "a@b.com",
                "chunk_count": 2,
                "embeddings_status": "ready",
                "vector_status": None,
                "error_message": None,
                "text_preview": None,
            }
        ],
    }
    with patch("app.api.v1.documents.firestore.Client", return_value=MagicMock()), patch(
        "app.api.v1.documents.get_document", return_value=raw
    ):
        res = client.get("/api/v1/documents/d1")
    assert res.status_code == 200
    body = res.json()
    assert body["document_id"] == "d1"
    assert len(body["versions"]) == 1
    assert body["versions"][0]["status"] == "ready"


def test_list_requires_auth_when_bypass_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_DEV_BYPASS", "false")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    get_settings.cache_clear()
    local = TestClient(app)
    assert local.get("/api/v1/documents").status_code == 401
