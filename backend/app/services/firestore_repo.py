"""Firestore repository for Document + Version metadata (Phase 2.1–2.3).

Collection layout (ADR-0006):
  documents/{document_id}
  documents/{document_id}/versions/{version_id}

Full extracted text lives in GCS processed/; Firestore keeps pointers + preview only.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Protocol

from google.cloud import firestore

logger = logging.getLogger("erp.api.firestore")

DOCUMENTS_COLLECTION = "documents"
VERSIONS_SUBCOLLECTION = "versions"
INITIAL_VERSION_STATUS = "processing"
STATUS_READY = "ready"
STATUS_FAILED = "failed"


class FirestoreClientLike(Protocol):
    def collection(self, name: str) -> Any: ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def version_ref(
    client: firestore.Client, document_id: str, version_id: str
) -> firestore.DocumentReference:
    return (
        client.collection(DOCUMENTS_COLLECTION)
        .document(document_id)
        .collection(VERSIONS_SUBCOLLECTION)
        .document(version_id)
    )


def create_document_with_version(
    client: firestore.Client,
    *,
    document_id: str,
    version_id: str,
    title: str | None,
    collection: str | None,
    gcs_uri: str,
    gcs_object_key: str,
    filename: str,
    content_type: str,
    size_bytes: int,
    created_by: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Atomically create document + version (status=processing) in a batch."""
    batch = client.batch()
    now = _utc_now()

    doc_ref = client.collection(DOCUMENTS_COLLECTION).document(document_id)
    v_ref = version_ref(client, document_id, version_id)

    doc_data: dict[str, Any] = {
        "document_id": document_id,
        # Prefer caller-resolved title (filename default in process_upload)
        "title": (title or "").strip() or "Untitled",
        "collection": collection,
        "active_version_id": None,
        "latest_version_id": version_id,
        "created_at": now,
        "updated_at": now,
        "created_by": created_by,
    }
    version_data: dict[str, Any] = {
        "version_id": version_id,
        "document_id": document_id,
        "status": INITIAL_VERSION_STATUS,
        "gcs_uri": gcs_uri,
        "gcs_object_key": gcs_object_key,
        "filename": filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "created_at": now,
        "created_by": created_by,
        "processed_gcs_prefix": None,
        "full_text_gcs_uri": None,
        "chunks_gcs_uri": None,
        "chunk_count": None,
        "text_preview": None,
        "extracted_char_count": None,
        "error_message": None,
        # Phase 3.1 embeddings (separate from content status)
        "embeddings_status": None,
        "embedding_model_id": None,
        "embedded_chunk_count": None,
        "embeddings_gcs_uri": None,
        "embeddings_error": None,
        # Phase 3.2 Vector Search
        "vector_status": None,
        "vector_error": None,
        "vector_datapoint_count": None,
    }

    batch.set(doc_ref, doc_data)
    batch.set(v_ref, version_data)
    batch.commit()

    logger.info(
        "firestore_document_version_created document_id=%s version_id=%s",
        document_id,
        version_id,
    )
    return doc_data, version_data


def update_version_ready(
    client: firestore.Client,
    *,
    document_id: str,
    version_id: str,
    processed_gcs_prefix: str,
    full_text_gcs_uri: str,
    chunks_gcs_uri: str,
    chunk_count: int,
    text_preview: str,
    extracted_char_count: int,
) -> dict[str, Any]:
    """
    Transition version processing → ready.

    Stores GCS pointers + short text_preview only (no full extracted_text).
    Clears legacy extracted_text field if present (Phase 2.2 → 2.3).
    """
    now = _utc_now()
    patch: dict[str, Any] = {
        "status": STATUS_READY,
        "processed_gcs_prefix": processed_gcs_prefix,
        "full_text_gcs_uri": full_text_gcs_uri,
        "chunks_gcs_uri": chunks_gcs_uri,
        "chunk_count": chunk_count,
        "text_preview": text_preview,
        "extracted_char_count": extracted_char_count,
        "error_message": None,
        "extracted_text": firestore.DELETE_FIELD,
        "extracted_truncated": firestore.DELETE_FIELD,
        "extraction_completed_at": now,
        "updated_at": now,
    }
    version_ref(client, document_id, version_id).update(patch)
    client.collection(DOCUMENTS_COLLECTION).document(document_id).update(
        {"updated_at": now}
    )
    logger.info(
        "firestore_version_ready document_id=%s version_id=%s chunks=%s chars=%s",
        document_id,
        version_id,
        chunk_count,
        extracted_char_count,
    )
    return {
        k: v for k, v in patch.items() if v is not firestore.DELETE_FIELD
    }


def update_version_embeddings_ready(
    client: firestore.Client,
    *,
    document_id: str,
    version_id: str,
    embedding_model_id: str,
    embedded_chunk_count: int,
    embeddings_gcs_uri: str,
) -> dict[str, Any]:
    """Mark embeddings successful (does not change content status)."""
    now = _utc_now()
    patch: dict[str, Any] = {
        "embeddings_status": "ready",
        "embedding_model_id": embedding_model_id,
        "embedded_chunk_count": embedded_chunk_count,
        "embeddings_gcs_uri": embeddings_gcs_uri,
        "embeddings_error": None,
        "embeddings_completed_at": now,
        "updated_at": now,
    }
    version_ref(client, document_id, version_id).update(patch)
    client.collection(DOCUMENTS_COLLECTION).document(document_id).update(
        {"updated_at": now}
    )
    logger.info(
        "firestore_embeddings_ready document_id=%s version_id=%s count=%s model=%s",
        document_id,
        version_id,
        embedded_chunk_count,
        embedding_model_id,
    )
    return patch


def update_version_embeddings_failed(
    client: firestore.Client,
    *,
    document_id: str,
    version_id: str,
    embedding_model_id: str,
    error_message: str,
) -> dict[str, Any]:
    """Mark embeddings failed; leave content status (ready) intact."""
    now = _utc_now()
    safe_error = (error_message or "Embedding failed")[:2000]
    patch: dict[str, Any] = {
        "embeddings_status": "failed",
        "embedding_model_id": embedding_model_id,
        "embedded_chunk_count": 0,
        "embeddings_gcs_uri": None,
        "embeddings_error": safe_error,
        "embeddings_completed_at": now,
        "updated_at": now,
    }
    version_ref(client, document_id, version_id).update(patch)
    client.collection(DOCUMENTS_COLLECTION).document(document_id).update(
        {"updated_at": now}
    )
    logger.info(
        "firestore_embeddings_failed document_id=%s version_id=%s",
        document_id,
        version_id,
    )
    return patch


def update_version_vector_status(
    client: firestore.Client,
    *,
    document_id: str,
    version_id: str,
    vector_status: str,
    vector_datapoint_count: int | None = None,
    vector_error: str | None = None,
) -> dict[str, Any]:
    """
    Update Vector Search lifecycle status on the version.

    vector_status: upserted | activated | deactivated | failed | skipped
    """
    now = _utc_now()
    patch: dict[str, Any] = {
        "vector_status": vector_status,
        "vector_error": (vector_error[:2000] if vector_error else None),
        "vector_updated_at": now,
        "updated_at": now,
    }
    if vector_datapoint_count is not None:
        patch["vector_datapoint_count"] = vector_datapoint_count
    version_ref(client, document_id, version_id).update(patch)
    client.collection(DOCUMENTS_COLLECTION).document(document_id).update(
        {"updated_at": now}
    )
    logger.info(
        "firestore_vector_status document_id=%s version_id=%s status=%s",
        document_id,
        version_id,
        vector_status,
    )
    return patch


def update_version_failed(
    client: firestore.Client,
    *,
    document_id: str,
    version_id: str,
    error_message: str,
) -> dict[str, Any]:
    """Transition version processing → failed and store error message."""
    now = _utc_now()
    safe_error = (error_message or "Processing failed")[:2000]
    patch: dict[str, Any] = {
        "status": STATUS_FAILED,
        "error_message": safe_error,
        "chunk_count": 0,
        "text_preview": None,
        "processed_gcs_prefix": None,
        "full_text_gcs_uri": None,
        "chunks_gcs_uri": None,
        "extracted_char_count": 0,
        "extracted_text": firestore.DELETE_FIELD,
        "extracted_truncated": firestore.DELETE_FIELD,
        "extraction_completed_at": now,
        "updated_at": now,
    }
    version_ref(client, document_id, version_id).update(patch)
    client.collection(DOCUMENTS_COLLECTION).document(document_id).update(
        {"updated_at": now}
    )
    logger.info(
        "firestore_version_failed document_id=%s version_id=%s",
        document_id,
        version_id,
    )
    return {
        k: v for k, v in patch.items() if v is not firestore.DELETE_FIELD
    }


# ── Read helpers (Phase 5.3 Admin UI) ────────────────────────────────────────


def _serialize_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # Firestore may return DatetimeWithNanoseconds (subclass of datetime)
    return None


def version_summary_from_data(version_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Normalize a version document for API responses."""
    return {
        "version_id": version_id,
        "status": data.get("status") or "processing",
        "filename": data.get("filename"),
        "gcs_uri": data.get("gcs_uri"),
        "content_type": data.get("content_type"),
        "size_bytes": data.get("size_bytes"),
        "created_at": _serialize_ts(data.get("created_at")),
        "created_by": data.get("created_by"),
        "chunk_count": data.get("chunk_count"),
        "embeddings_status": data.get("embeddings_status"),
        "vector_status": data.get("vector_status"),
        "error_message": data.get("error_message"),
        "text_preview": data.get("text_preview"),
    }


def get_version(
    client: FirestoreClientLike,
    document_id: str,
    version_id: str,
) -> dict[str, Any] | None:
    ref = (
        client.collection(DOCUMENTS_COLLECTION)
        .document(document_id)
        .collection(VERSIONS_SUBCOLLECTION)
        .document(version_id)
    )
    snap = ref.get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    return version_summary_from_data(version_id, data)


def get_document(
    client: FirestoreClientLike,
    document_id: str,
    *,
    include_versions: bool = True,
) -> dict[str, Any] | None:
    """Return document metadata and optionally all versions (newest first)."""
    doc_ref = client.collection(DOCUMENTS_COLLECTION).document(document_id)
    snap = doc_ref.get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    out: dict[str, Any] = {
        "document_id": document_id,
        "title": data.get("title"),
        "collection": data.get("collection"),
        "active_version_id": data.get("active_version_id"),
        "latest_version_id": data.get("latest_version_id"),
        "created_at": _serialize_ts(data.get("created_at")),
        "updated_at": _serialize_ts(data.get("updated_at")),
        "created_by": data.get("created_by"),
    }
    if include_versions:
        versions: list[dict[str, Any]] = []
        for v_snap in doc_ref.collection(VERSIONS_SUBCOLLECTION).stream():
            v_data = v_snap.to_dict() or {}
            versions.append(version_summary_from_data(v_snap.id, v_data))
        # Newest first by created_at when available
        versions.sort(
            key=lambda v: v.get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        out["versions"] = versions
        # Convenience pointer for list-style cards
        latest_id = out.get("latest_version_id")
        out["latest_version"] = next(
            (v for v in versions if v["version_id"] == latest_id),
            versions[0] if versions else None,
        )
    return out


def list_documents(
    client: FirestoreClientLike,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List documents (most recently updated first), with latest version summary."""
    limit = max(1, min(limit, 100))
    col = client.collection(DOCUMENTS_COLLECTION)
    try:
        query = col.order_by(
            "updated_at", direction=firestore.Query.DESCENDING
        ).limit(limit)
        snaps = list(query.stream())
    except Exception:
        # Missing index or field — fall back to unordered limited scan
        logger.warning("list_documents_order_by_fallback")
        snaps = list(col.limit(limit).stream())

    results: list[dict[str, Any]] = []
    for snap in snaps:
        doc = get_document(client, snap.id, include_versions=True)
        if doc:
            # Drop full versions list on list endpoint payload (keep latest only)
            versions = doc.pop("versions", [])
            if not doc.get("latest_version") and versions:
                doc["latest_version"] = versions[0]
            results.append(doc)
    return results
