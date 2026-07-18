"""GCS write helpers for raw uploads and processed artifacts (Phase 2.1–3.1)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Protocol, Sequence

from google.cloud import storage

from app.services.chunking import Chunk
from app.services.embeddings import EmbeddingRecord

logger = logging.getLogger("erp.api.gcs")

_UNSAFE_FILENAME = re.compile(r"[^\w.\- ()\[\]]+", re.UNICODE)
_MAX_FILENAME_LEN = 200


class StorageClient(Protocol):
    """Minimal protocol so tests can inject a fake client."""

    def bucket(self, name: str) -> object: ...


@dataclass(frozen=True, slots=True)
class GcsUploadResult:
    bucket: str
    object_key: str
    gcs_uri: str
    size_bytes: int
    content_type: str
    filename: str


@dataclass(frozen=True, slots=True)
class ProcessedArtifacts:
    """Pointers written under processed/{document_id}/{version_id}/."""

    bucket: str
    prefix: str
    full_text_object_key: str
    chunks_object_key: str
    full_text_gcs_uri: str
    chunks_gcs_uri: str
    chunk_count: int
    full_text_char_count: int


def sanitize_filename(original: str | None) -> str:
    """Return a path-safe basename for GCS object keys."""
    name = (original or "upload.bin").strip().replace("\\", "/")
    name = name.split("/")[-1] or "upload.bin"
    name = _UNSAFE_FILENAME.sub("_", name).strip("._ ") or "upload.bin"
    if len(name) > _MAX_FILENAME_LEN:
        if "." in name:
            stem, ext = name.rsplit(".", 1)
            ext = ext[:20]
            stem = stem[: max(1, _MAX_FILENAME_LEN - len(ext) - 1)]
            name = f"{stem}.{ext}"
        else:
            name = name[:_MAX_FILENAME_LEN]
    return name


def build_raw_object_key(
    document_id: str, version_id: str, filename: str
) -> str:
    """raw/{document_id}/{version_id}/{safe_filename}."""
    safe = sanitize_filename(filename)
    return f"raw/{document_id}/{version_id}/{safe}"


def build_processed_prefix(document_id: str, version_id: str) -> str:
    """processed/{document_id}/{version_id}/ (trailing slash)."""
    return f"processed/{document_id}/{version_id}/"


def build_full_text_object_key(document_id: str, version_id: str) -> str:
    return f"{build_processed_prefix(document_id, version_id)}full.txt"


def build_chunks_object_key(document_id: str, version_id: str) -> str:
    return f"{build_processed_prefix(document_id, version_id)}chunks.jsonl"


def build_embeddings_object_key(document_id: str, version_id: str) -> str:
    return f"{build_processed_prefix(document_id, version_id)}embeddings.jsonl"


def upload_raw_bytes(
    *,
    client: storage.Client,
    bucket_name: str,
    document_id: str,
    version_id: str,
    filename: str,
    data: bytes,
    content_type: str,
) -> GcsUploadResult:
    """Write upload bytes to the raw/ prefix. Returns gs:// URI metadata."""
    object_key = build_raw_object_key(document_id, version_id, filename)
    safe_name = sanitize_filename(filename)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_key)
    blob.upload_from_string(data, content_type=content_type)
    gcs_uri = f"gs://{bucket_name}/{object_key}"
    logger.info(
        "gcs_upload_ok bucket=%s key=%s size_bytes=%s",
        bucket_name,
        object_key,
        len(data),
    )
    return GcsUploadResult(
        bucket=bucket_name,
        object_key=object_key,
        gcs_uri=gcs_uri,
        size_bytes=len(data),
        content_type=content_type,
        filename=safe_name,
    )


def _chunks_to_jsonl(chunks: Sequence[Chunk]) -> str:
    lines = [json.dumps(c.to_jsonl_dict(), ensure_ascii=False) for c in chunks]
    return "\n".join(lines) + ("\n" if lines else "")


def write_processed_artifacts(
    *,
    client: storage.Client,
    bucket_name: str,
    document_id: str,
    version_id: str,
    full_text: str,
    chunks: Sequence[Chunk],
) -> ProcessedArtifacts:
    """
    Write full.txt and chunks.jsonl under processed/{document_id}/{version_id}/.
    """
    prefix = build_processed_prefix(document_id, version_id)
    full_key = build_full_text_object_key(document_id, version_id)
    chunks_key = build_chunks_object_key(document_id, version_id)

    bucket = client.bucket(bucket_name)
    full_blob = bucket.blob(full_key)
    full_blob.upload_from_string(
        full_text.encode("utf-8"),
        content_type="text/plain; charset=utf-8",
    )

    chunks_blob = bucket.blob(chunks_key)
    chunks_payload = _chunks_to_jsonl(chunks)
    chunks_blob.upload_from_string(
        chunks_payload.encode("utf-8"),
        content_type="application/x-ndjson; charset=utf-8",
    )

    full_uri = f"gs://{bucket_name}/{full_key}"
    chunks_uri = f"gs://{bucket_name}/{chunks_key}"
    logger.info(
        "gcs_processed_ok bucket=%s prefix=%s chunks=%s chars=%s",
        bucket_name,
        prefix,
        len(chunks),
        len(full_text),
    )
    return ProcessedArtifacts(
        bucket=bucket_name,
        prefix=prefix,
        full_text_object_key=full_key,
        chunks_object_key=chunks_key,
        full_text_gcs_uri=full_uri,
        chunks_gcs_uri=chunks_uri,
        chunk_count=len(chunks),
        full_text_char_count=len(full_text),
    )


@dataclass(frozen=True, slots=True)
class EmbeddingsArtifact:
    """Pointer to embeddings.jsonl under processed/."""

    bucket: str
    object_key: str
    gcs_uri: str
    embedded_chunk_count: int
    embedding_model_id: str


def write_embeddings_jsonl(
    *,
    client: storage.Client,
    bucket_name: str,
    document_id: str,
    version_id: str,
    records: Sequence[EmbeddingRecord],
    embedding_model_id: str,
) -> EmbeddingsArtifact:
    """Write embeddings.jsonl under processed/{document_id}/{version_id}/."""
    object_key = build_embeddings_object_key(document_id, version_id)
    lines = [json.dumps(r.to_jsonl_dict(), ensure_ascii=False) for r in records]
    payload = "\n".join(lines) + ("\n" if lines else "")

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_key)
    blob.upload_from_string(
        payload.encode("utf-8"),
        content_type="application/x-ndjson; charset=utf-8",
    )
    gcs_uri = f"gs://{bucket_name}/{object_key}"
    logger.info(
        "gcs_embeddings_ok bucket=%s key=%s count=%s model=%s",
        bucket_name,
        object_key,
        len(records),
        embedding_model_id,
    )
    return EmbeddingsArtifact(
        bucket=bucket_name,
        object_key=object_key,
        gcs_uri=gcs_uri,
        embedded_chunk_count=len(records),
        embedding_model_id=embedding_model_id,
    )
