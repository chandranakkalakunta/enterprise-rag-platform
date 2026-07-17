"""Phase 2.1–2.2 — document upload API tests (mocked GCS + Firestore + extraction)."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.services.gcs_storage import build_raw_object_key, sanitize_filename
from app.services.upload import (
    ALLOWED_CONTENT_TYPES,
    UploadValidationError,
    validate_upload,
)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings_dev_bypass(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("AUTH_DEV_BYPASS", "true")
    monkeypatch.setenv("GCS_DOCS_BUCKET", "rag-docs-dev")
    monkeypatch.setenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024))
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def client(settings_dev_bypass: Settings) -> TestClient:
    return TestClient(app)


def _mock_storage_and_firestore():
    """Patch GCS + Firestore clients used by process_upload."""
    storage_client = MagicMock(name="storage.Client")
    bucket = MagicMock(name="bucket")
    blob = MagicMock(name="blob")
    storage_client.bucket.return_value = bucket
    bucket.blob.return_value = blob

    firestore_client = MagicMock(name="firestore.Client")
    batch = MagicMock(name="batch")
    firestore_client.batch.return_value = batch

    doc_ref = MagicMock(name="doc_ref")
    version_ref = MagicMock(name="version_ref")
    versions_col = MagicMock(name="versions_col")
    docs_col = MagicMock(name="docs_col")

    firestore_client.collection.return_value = docs_col
    docs_col.document.return_value = doc_ref
    doc_ref.collection.return_value = versions_col
    versions_col.document.return_value = version_ref

    return storage_client, firestore_client, blob, batch, version_ref, doc_ref


# ── Unit: validation helpers ────────────────────────────────────────────────


def test_validate_markdown_content_type() -> None:
    ct = validate_upload(
        content_type="text/markdown",
        filename="notes.md",
        size_bytes=12,
        max_bytes=50 * 1024 * 1024,
    )
    assert ct == "text/markdown"


def test_validate_pdf_content_type() -> None:
    ct = validate_upload(
        content_type="application/pdf",
        filename="doc.pdf",
        size_bytes=100,
        max_bytes=50 * 1024 * 1024,
    )
    assert ct == "application/pdf"


def test_validate_rejects_unsupported_type() -> None:
    with pytest.raises(UploadValidationError, match="Unsupported media type"):
        validate_upload(
            content_type="application/msword",
            filename="x.doc",
            size_bytes=10,
            max_bytes=50 * 1024 * 1024,
        )


def test_validate_rejects_oversized() -> None:
    with pytest.raises(UploadValidationError, match="File too large"):
        validate_upload(
            content_type="text/markdown",
            filename="big.md",
            size_bytes=50 * 1024 * 1024 + 1,
            max_bytes=50 * 1024 * 1024,
        )


def test_validate_rejects_empty() -> None:
    with pytest.raises(UploadValidationError, match="Empty"):
        validate_upload(
            content_type="text/markdown",
            filename="empty.md",
            size_bytes=0,
            max_bytes=50 * 1024 * 1024,
        )


def test_validate_octet_stream_md_extension() -> None:
    ct = validate_upload(
        content_type="application/octet-stream",
        filename="readme.md",
        size_bytes=5,
        max_bytes=100,
    )
    assert ct == "text/markdown"


def test_sanitize_filename_strips_path() -> None:
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert ".." not in sanitize_filename("a/b/c.md")


def test_build_raw_object_key() -> None:
    key = build_raw_object_key("doc-1", "ver-1", "My File.md")
    assert key == "raw/doc-1/ver-1/My File.md"


# ── API: success path (extraction → ready) ──────────────────────────────────


def test_upload_markdown_success_ready(client: TestClient) -> None:
    storage_client, firestore_client, blob, batch, version_ref, _doc = (
        _mock_storage_and_firestore()
    )

    with (
        patch("app.services.upload.storage.Client", return_value=storage_client),
        patch("app.services.upload.firestore.Client", return_value=firestore_client),
        patch(
            "app.services.upload.new_ids",
            return_value=("doc-aaa", "ver-bbb"),
        ),
    ):
        content = b"# Hello RAG\n\nBody text.\n"
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("hello.md", BytesIO(content), "text/markdown")},
            data={"title": "Hello", "collection": "policies"},
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["document_id"] == "doc-aaa"
    assert body["version_id"] == "ver-bbb"
    assert body["status"] == "ready"
    assert body["gcs_uri"] == "gs://rag-docs-dev/raw/doc-aaa/ver-bbb/hello.md"
    assert body["filename"] == "hello.md"
    assert body["content_type"] == "text/markdown"
    assert body["size_bytes"] == len(content)
    assert body["title"] == "Hello"
    assert body["collection"] == "policies"
    assert body["error_message"] is None
    assert body["extracted_char_count"] is not None
    assert body["extracted_char_count"] > 0
    assert body["extracted_truncated"] is False

    blob.upload_from_string.assert_called_once()
    batch.commit.assert_called_once()
    # status update after extraction
    version_ref.update.assert_called_once()
    update_payload = version_ref.update.call_args[0][0]
    assert update_payload["status"] == "ready"
    assert "Hello RAG" in update_payload["extracted_text"] or "Body text" in (
        update_payload["extracted_text"] or ""
    )


def test_upload_pdf_success_ready(client: TestClient) -> None:
    storage_client, firestore_client, _blob, _batch, version_ref, _ = (
        _mock_storage_and_firestore()
    )
    pdf_bytes = b"%PDF-1.4 fake content for upload test"

    with (
        patch("app.services.upload.storage.Client", return_value=storage_client),
        patch("app.services.upload.firestore.Client", return_value=firestore_client),
        patch(
            "app.services.upload.new_ids",
            return_value=("doc-pdf", "ver-pdf"),
        ),
        patch(
            "app.services.extraction.pdfminer_extract_text",
            return_value="Extracted PDF body",
        ),
    ):
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("report.pdf", BytesIO(pdf_bytes), "application/pdf")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert body["content_type"] == "application/pdf"
    assert body["gcs_uri"].endswith("/report.pdf")
    assert "raw/doc-pdf/ver-pdf/" in body["gcs_uri"]
    assert body["extracted_char_count"] == len("Extracted PDF body")
    version_ref.update.assert_called_once()
    assert version_ref.update.call_args[0][0]["status"] == "ready"


def test_upload_extraction_failure_status_failed(client: TestClient) -> None:
    """Bad PDF header → extraction fails → 201 with status=failed."""
    storage_client, firestore_client, _blob, _batch, version_ref, _ = (
        _mock_storage_and_firestore()
    )
    # Pass content-type PDF but body without %PDF — extractor fails after GCS+FS
    bad_pdf = b"this is not a real pdf"

    with (
        patch("app.services.upload.storage.Client", return_value=storage_client),
        patch("app.services.upload.firestore.Client", return_value=firestore_client),
        patch("app.services.upload.new_ids", return_value=("doc-f", "ver-f")),
    ):
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("bad.pdf", BytesIO(bad_pdf), "application/pdf")},
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_message"]
    assert "PDF" in body["error_message"] or "pdf" in body["error_message"].lower()
    update_payload = version_ref.update.call_args[0][0]
    assert update_payload["status"] == "failed"
    assert update_payload["error_message"]


# ── API: error paths ────────────────────────────────────────────────────────


def test_upload_rejects_unsupported_media_type(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("x.docx", BytesIO(b"fake"), "application/vnd.openxmlformats")},
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


def test_upload_rejects_oversized_file(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "100")
    get_settings.cache_clear()
    local = TestClient(app)

    big = b"x" * 101
    response = local.post(
        "/api/v1/documents/upload",
        files={"file": ("big.md", BytesIO(big), "text/markdown")},
    )
    assert response.status_code == 400
    assert "too large" in response.json()["detail"].lower()


def test_upload_gcs_failure_returns_500(client: TestClient) -> None:
    storage_client = MagicMock()
    storage_client.bucket.side_effect = RuntimeError("GCS down")

    with (
        patch("app.services.upload.storage.Client", return_value=storage_client),
        patch("app.services.upload.new_ids", return_value=("d1", "v1")),
    ):
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("a.md", BytesIO(b"# a"), "text/markdown")},
        )

    assert response.status_code == 500
    assert "GCS" in response.json()["detail"]


def test_upload_firestore_failure_returns_500(client: TestClient) -> None:
    storage_client, firestore_client, _blob, batch, _, _ = (
        _mock_storage_and_firestore()
    )
    batch.commit.side_effect = RuntimeError("Firestore down")

    with (
        patch("app.services.upload.storage.Client", return_value=storage_client),
        patch("app.services.upload.firestore.Client", return_value=firestore_client),
        patch("app.services.upload.new_ids", return_value=("d2", "v2")),
    ):
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("a.md", BytesIO(b"# a"), "text/markdown")},
        )

    assert response.status_code == 500
    assert "metadata" in response.json()["detail"].lower()


def test_upload_requires_bearer_when_bypass_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_DEV_BYPASS", "false")
    monkeypatch.setenv("UPLOAD_BEARER_TOKEN", "secret-token")
    get_settings.cache_clear()
    local = TestClient(app)

    response = local.post(
        "/api/v1/documents/upload",
        files={"file": ("a.md", BytesIO(b"# a"), "text/markdown")},
    )
    assert response.status_code == 401

    storage_client, firestore_client, _, _, _, _ = _mock_storage_and_firestore()
    with (
        patch("app.services.upload.storage.Client", return_value=storage_client),
        patch("app.services.upload.firestore.Client", return_value=firestore_client),
        patch("app.services.upload.new_ids", return_value=("d3", "v3")),
    ):
        ok = local.post(
            "/api/v1/documents/upload",
            files={"file": ("a.md", BytesIO(b"# a"), "text/markdown")},
            headers={"Authorization": "Bearer secret-token"},
        )
    assert ok.status_code == 201
    assert ok.json()["status"] == "ready"


def test_allowed_content_types_constant() -> None:
    assert "application/pdf" in ALLOWED_CONTENT_TYPES
    assert "text/markdown" in ALLOWED_CONTENT_TYPES
    assert "text/x-markdown" in ALLOWED_CONTENT_TYPES


def test_response_schema_keys(client: TestClient) -> None:
    storage_client, firestore_client, _, _, _, _ = _mock_storage_and_firestore()
    with (
        patch("app.services.upload.storage.Client", return_value=storage_client),
        patch("app.services.upload.firestore.Client", return_value=firestore_client),
        patch("app.services.upload.new_ids", return_value=("dx", "vx")),
    ):
        body = client.post(
            "/api/v1/documents/upload",
            files={"file": ("a.md", BytesIO(b"# a"), "text/markdown")},
        ).json()

    expected = {
        "document_id",
        "version_id",
        "status",
        "gcs_uri",
        "filename",
        "content_type",
        "size_bytes",
        "title",
        "collection",
        "extracted_char_count",
        "extracted_truncated",
        "error_message",
    }
    assert expected.issubset(body.keys())
    assert isinstance(body["size_bytes"], int)
    assert body["status"] in ("ready", "failed")
