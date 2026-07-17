"""Unit tests for GCS path helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.services.gcs_storage import (
    build_raw_object_key,
    sanitize_filename,
    upload_raw_bytes,
)


def test_upload_raw_bytes_writes_blob() -> None:
    client = MagicMock()
    bucket = MagicMock()
    blob = MagicMock()
    client.bucket.return_value = bucket
    bucket.blob.return_value = blob

    result = upload_raw_bytes(
        client=client,
        bucket_name="rag-docs-dev",
        document_id="d1",
        version_id="v1",
        filename="policy.pdf",
        data=b"%PDF",
        content_type="application/pdf",
    )

    client.bucket.assert_called_once_with("rag-docs-dev")
    bucket.blob.assert_called_once_with("raw/d1/v1/policy.pdf")
    blob.upload_from_string.assert_called_once_with(
        b"%PDF", content_type="application/pdf"
    )
    assert result.gcs_uri == "gs://rag-docs-dev/raw/d1/v1/policy.pdf"
    assert result.size_bytes == 4
    assert result.filename == "policy.pdf"


def test_sanitize_long_filename() -> None:
    long = "a" * 300 + ".md"
    out = sanitize_filename(long)
    assert len(out) <= 200
    assert out.endswith(".md")


def test_object_key_convention() -> None:
    assert build_raw_object_key("a", "b", "c.md") == "raw/a/b/c.md"
