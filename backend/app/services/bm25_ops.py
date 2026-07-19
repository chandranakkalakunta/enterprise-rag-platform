"""BM25 index load/upsert from GCS published versions (Phase 4.2)."""

from __future__ import annotations

import json
import logging
from typing import Any

from google.cloud import storage

from app.core.config import Settings
from app.services.bm25_index import Bm25Chunk, InProcessBM25Index, get_bm25_index
from app.services.gcs_storage import build_chunks_object_key, read_object_bytes

logger = logging.getLogger("erp.api.bm25_ops")


def parse_chunks_jsonl(data: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in data.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def chunks_from_jsonl_rows(
    rows: list[dict[str, Any]],
    *,
    document_id: str,
    version_id: str,
    title: str | None = None,
    filename: str | None = None,
    collection: str | None = None,
) -> list[Bm25Chunk]:
    out: list[Bm25Chunk] = []
    for row in rows:
        idx = int(row.get("index", row.get("chunk_id", 0)))
        text = str(row.get("text") or "")
        if not text.strip():
            continue
        out.append(
            Bm25Chunk(
                document_id=document_id,
                version_id=version_id,
                chunk_index=idx,
                text=text,
                title=title,
                filename=filename,
                collection=collection,
            )
        )
    return out


def load_version_bm25_chunks(
    *,
    gcs_client: storage.Client,
    bucket_name: str,
    document_id: str,
    version_id: str,
    title: str | None = None,
    filename: str | None = None,
    collection: str | None = None,
) -> list[Bm25Chunk]:
    """Load processed chunks.jsonl for a version into Bm25Chunk list."""
    key = build_chunks_object_key(document_id, version_id)
    raw = read_object_bytes(
        client=gcs_client, bucket_name=bucket_name, object_key=key
    )
    rows = parse_chunks_jsonl(raw)
    return chunks_from_jsonl_rows(
        rows,
        document_id=document_id,
        version_id=version_id,
        title=title,
        filename=filename,
        collection=collection,
    )


def bm25_index_published_version(
    *,
    settings: Settings,
    gcs_client: storage.Client,
    document_id: str,
    version_id: str,
    title: str | None = None,
    filename: str | None = None,
    collection: str | None = None,
    previous_version_id: str | None = None,
    index: InProcessBM25Index | None = None,
) -> str:
    """
    After publish: remove previous published version (if any), upsert new version.

    Returns status string: indexed | skipped | failed
    """
    if not settings.hybrid_retrieval_enabled and not settings.bm25_always_index:
        return "skipped"

    idx = index or get_bm25_index()
    try:
        if previous_version_id:
            idx.remove_version(document_id, previous_version_id)
        # Also clear same version if re-publish edge case
        idx.remove_version(document_id, version_id)
        chunks = load_version_bm25_chunks(
            gcs_client=gcs_client,
            bucket_name=settings.gcs_docs_bucket,
            document_id=document_id,
            version_id=version_id,
            title=title,
            filename=filename,
            collection=collection,
        )
        n = idx.upsert_chunks(chunks)
        logger.info(
            "bm25_publish_indexed document_id=%s version_id=%s chunks=%s",
            document_id,
            version_id,
            n,
        )
        return "indexed"
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "bm25_publish_failed document_id=%s version_id=%s err=%s",
            document_id,
            version_id,
            exc,
        )
        return "failed"


def bm25_remove_version(
    *,
    document_id: str,
    version_id: str,
    index: InProcessBM25Index | None = None,
    enabled: bool = True,
) -> str:
    """After retire: remove version from BM25 index."""
    if not enabled:
        return "skipped"
    idx = index or get_bm25_index()
    try:
        n = idx.remove_version(document_id, version_id)
        logger.info(
            "bm25_retire_removed document_id=%s version_id=%s removed=%s",
            document_id,
            version_id,
            n,
        )
        return "removed"
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "bm25_retire_failed document_id=%s version_id=%s err=%s",
            document_id,
            version_id,
            exc,
        )
        return "failed"
