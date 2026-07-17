"""Unit tests for GCS path helpers and processed writers."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.services.chunking import Chunk
from app.services.gcs_storage import (
    build_chunks_object_key,
    build_full_text_object_key,
    build_processed_prefix,
    build_raw_object_key,
    sanitize_filename,
    upload_raw_bytes,
    write_processed_artifacts,
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
    assert build_processed_prefix("a", "b") == "processed/a/b/"
    assert build_full_text_object_key("a", "b") == "processed/a/b/full.txt"
    assert build_chunks_object_key("a", "b") == "processed/a/b/chunks.jsonl"


def test_write_processed_artifacts() -> None:
    client = MagicMock()
    bucket = MagicMock()
    full_blob = MagicMock()
    chunks_blob = MagicMock()
    client.bucket.return_value = bucket

    def _blob(key: str):
        if key.endswith("full.txt"):
            return full_blob
        return chunks_blob

    bucket.blob.side_effect = _blob

    chunks = [
        Chunk(index=0, text="hello ", char_count=6, start_offset=0, end_offset=6),
        Chunk(index=1, text="world", char_count=5, start_offset=6, end_offset=11),
    ]
    result = write_processed_artifacts(
        client=client,
        bucket_name="rag-docs-dev",
        document_id="doc1",
        version_id="ver1",
        full_text="hello world",
        chunks=chunks,
    )

    assert result.prefix == "processed/doc1/ver1/"
    assert result.chunk_count == 2
    assert result.full_text_gcs_uri == "gs://rag-docs-dev/processed/doc1/ver1/full.txt"
    assert result.chunks_gcs_uri == "gs://rag-docs-dev/processed/doc1/ver1/chunks.jsonl"
    full_blob.upload_from_string.assert_called_once()
    chunks_blob.upload_from_string.assert_called_once()
    payload = chunks_blob.upload_from_string.call_args[0][0]
    assert b'"index": 0' in payload or b'"index":0' in payload
    assert b"hello" in payload
