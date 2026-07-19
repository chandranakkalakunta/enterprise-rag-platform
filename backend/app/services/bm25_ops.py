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


def list_published_pointers(
    fs_client: Any,
    *,
    max_docs: int = 200,
) -> list[dict[str, Any]]:
    """Return {document_id, version_id, title, collection, filename?} for active pubs."""
    from app.services.firestore_repo import DOCUMENTS_COLLECTION, VERSIONS_SUBCOLLECTION

    out: list[dict[str, Any]] = []
    col = fs_client.collection(DOCUMENTS_COLLECTION)
    # Prefer documents that have an active published pointer
    try:
        snaps = list(col.limit(max(1, max_docs)).stream())
    except Exception as exc:  # noqa: BLE001
        logger.warning("bm25_list_docs_failed err=%s", exc)
        return []

    for snap in snaps:
        data = snap.to_dict() or {}
        active = data.get("active_version_id")
        if not active:
            continue
        version_id = str(active)
        document_id = str(snap.id)
        filename = None
        try:
            v_snap = (
                col.document(document_id)
                .collection(VERSIONS_SUBCOLLECTION)
                .document(version_id)
                .get()
            )
            if v_snap.exists:
                v_data = v_snap.to_dict() or {}
                filename = v_data.get("filename")
                # Only index if version still published
                if (v_data.get("status") or "") not in ("published",):
                    continue
        except Exception:  # noqa: BLE001
            pass
        out.append(
            {
                "document_id": document_id,
                "version_id": version_id,
                "title": data.get("title"),
                "collection": data.get("collection"),
                "filename": filename,
            }
        )
        if len(out) >= max_docs:
            break
    return out


def rebuild_bm25_from_published(
    *,
    settings: Settings,
    gcs_client: storage.Client | None = None,
    fs_client: Any | None = None,
    index: InProcessBM25Index | None = None,
) -> dict[str, Any]:
    """
    Rebuild in-process BM25 from all currently published versions.

    Never raises to callers when used from startup (returns status dict).
    """
    if not settings.hybrid_retrieval_enabled and not settings.bm25_always_index:
        return {"status": "skipped", "reason": "hybrid_disabled", "documents": 0, "chunks": 0}

    idx = index or get_bm25_index()
    try:
        from google.cloud import firestore as fs_mod

        gcs = gcs_client or storage.Client(project=settings.gcp_project_id)
        firestore_client = fs_client or fs_mod.Client(project=settings.gcp_project_id)
        pointers = list_published_pointers(
            firestore_client, max_docs=settings.bm25_warm_start_max_docs
        )
        idx.clear()
        total_chunks = 0
        ok_docs = 0
        failed_docs = 0
        for p in pointers:
            try:
                chunks = load_version_bm25_chunks(
                    gcs_client=gcs,
                    bucket_name=settings.gcs_docs_bucket,
                    document_id=p["document_id"],
                    version_id=p["version_id"],
                    title=p.get("title"),
                    filename=p.get("filename"),
                    collection=p.get("collection"),
                )
                total_chunks += idx.upsert_chunks(chunks)
                ok_docs += 1
            except Exception as exc:  # noqa: BLE001
                failed_docs += 1
                logger.warning(
                    "bm25_warm_doc_failed document_id=%s version_id=%s err=%s",
                    p.get("document_id"),
                    p.get("version_id"),
                    exc,
                )
        result = {
            "status": "ok",
            "documents": ok_docs,
            "failed_documents": failed_docs,
            "chunks": total_chunks,
            "index_size": idx.size(),
        }
        logger.info(
            "bm25_warm_start_complete documents=%s failed=%s chunks=%s index_size=%s",
            ok_docs,
            failed_docs,
            total_chunks,
            idx.size(),
        )
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("bm25_warm_start_failed err=%s", exc)
        return {
            "status": "failed",
            "error": str(exc),
            "documents": 0,
            "chunks": 0,
        }
