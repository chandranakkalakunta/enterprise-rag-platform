"""Firestore repository for Document + Version metadata (Phase 2.1).

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


class FirestoreClientLike(Protocol):
    def collection(self, name: str) -> Any: ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    }
    (
        client.collection(DOCUMENTS_COLLECTION)
        .document(document_id)
        .collection(VERSIONS_SUBCOLLECTION)
        .document(version_id)
        .set(data)
    )
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
    """Atomically create document + version in a single transaction batch."""
    batch = client.batch()
    now = _utc_now()

    doc_ref = client.collection(DOCUMENTS_COLLECTION).document(document_id)
    version_ref = doc_ref.collection(VERSIONS_SUBCOLLECTION).document(version_id)

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
    }

    batch.set(doc_ref, doc_data)
    batch.set(version_ref, version_data)
    batch.commit()

    logger.info(
        "firestore_document_version_created document_id=%s version_id=%s",
        document_id,
        version_id,
    )
    return doc_data, version_data
