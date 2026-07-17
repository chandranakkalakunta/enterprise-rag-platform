"""Firestore repository for Document + Version metadata (Phase 2.1–2.2).

Collection layout (ADR-0006):
  documents/{document_id}
  documents/{document_id}/versions/{version_id}
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


def create_document(
    client: firestore.Client,
    *,
    document_id: str,
    title: str | None,
    collection: str | None,
    latest_version_id: str,
    created_by: str,
) -> dict[str, Any]:
    """Create the parent document entity. Returns the stored dict."""
    now = _utc_now()
    data: dict[str, Any] = {
        "document_id": document_id,
        "title": title or "Untitled",
        "collection": collection,
        "active_version_id": None,
        "latest_version_id": latest_version_id,
        "created_at": now,
        "updated_at": now,
        "created_by": created_by,
    }
    client.collection(DOCUMENTS_COLLECTION).document(document_id).set(data)
    logger.info("firestore_document_created document_id=%s", document_id)
    return data


def create_version(
    client: firestore.Client,
    *,
    document_id: str,
    version_id: str,
    status: str = INITIAL_VERSION_STATUS,
    gcs_uri: str,
    gcs_object_key: str,
    filename: str,
    content_type: str,
    size_bytes: int,
    created_by: str,
) -> dict[str, Any]:
    """Create version under documents/{id}/versions/{version_id}."""
    now = _utc_now()
    data: dict[str, Any] = {
        "version_id": version_id,
        "document_id": document_id,
        "status": status,
        "gcs_uri": gcs_uri,
        "gcs_object_key": gcs_object_key,
        "filename": filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "created_at": now,
        "created_by": created_by,
        "extracted_text": None,
        "extracted_char_count": None,
        "extracted_truncated": False,
        "error_message": None,
    }
    version_ref(client, document_id, version_id).set(data)
    logger.info(
        "firestore_version_created document_id=%s version_id=%s status=%s",
        document_id,
        version_id,
        status,
    )
    return data


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
        "extracted_text": None,
        "extracted_char_count": None,
        "extracted_truncated": False,
        "error_message": None,
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


def update_version_extraction_success(
    client: firestore.Client,
    *,
    document_id: str,
    version_id: str,
    extracted_text: str,
    extracted_char_count: int,
    extracted_truncated: bool,
) -> dict[str, Any]:
    """Transition version processing → ready and store extracted text."""
    now = _utc_now()
    patch: dict[str, Any] = {
        "status": STATUS_READY,
        "extracted_text": extracted_text,
        "extracted_char_count": extracted_char_count,
        "extracted_truncated": extracted_truncated,
        "error_message": None,
        "extraction_completed_at": now,
        "updated_at": now,
    }
    version_ref(client, document_id, version_id).update(patch)
    # Touch parent document updated_at
    client.collection(DOCUMENTS_COLLECTION).document(document_id).update(
        {"updated_at": now}
    )
    logger.info(
        "firestore_version_ready document_id=%s version_id=%s chars=%s truncated=%s",
        document_id,
        version_id,
        extracted_char_count,
        extracted_truncated,
    )
    return patch


def update_version_extraction_failure(
    client: firestore.Client,
    *,
    document_id: str,
    version_id: str,
    error_message: str,
) -> dict[str, Any]:
    """Transition version processing → failed and store error message."""
    now = _utc_now()
    # Keep error messages bounded for API/logs (no full stack traces)
    safe_error = (error_message or "Extraction failed")[:2000]
    patch: dict[str, Any] = {
        "status": STATUS_FAILED,
        "error_message": safe_error,
        "extracted_text": None,
        "extracted_char_count": 0,
        "extracted_truncated": False,
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
    return patch
