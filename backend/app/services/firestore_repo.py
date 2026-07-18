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
        "title": title or "Untitled",
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
