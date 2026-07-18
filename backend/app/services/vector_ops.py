"""Orchestrate Vector Search upsert/activate from GCS artifacts (Phase 3.2)."""

from __future__ import annotations

import logging
from typing import Any

from google.cloud import firestore, storage

from app.core.config import Settings
from app.services.firestore_repo import update_version_vector_status
from app.services.gcs_storage import (
    build_chunks_object_key,
    build_embeddings_object_key,
    read_object_bytes,
)
from app.services.vector_search import (
    VectorIndexClient,
    VectorSearchError,
    VertexIndexClient,
    join_chunks_and_embeddings,
    parse_jsonl_bytes,
    set_active_for_version,
    upsert_version_vectors,
)

logger = logging.getLogger("erp.api.vector_ops")


def _vector_configured(settings: Settings) -> bool:
    return bool(
        settings.vector_search_enabled and (settings.vector_search_index_id or "").strip()
    )


def _make_client(settings: Settings) -> VertexIndexClient:
    return VertexIndexClient(
        project_id=settings.gcp_project_id,
        location=settings.vector_search_region,
        index_id=settings.vector_search_index_id.strip(),
    )


def load_version_chunk_embeddings(
    *,
    gcs_client: storage.Client,
    bucket_name: str,
    document_id: str,
    version_id: str,
) -> list:
    """Load and join chunks.jsonl + embeddings.jsonl from GCS."""
    chunks_key = build_chunks_object_key(document_id, version_id)
    emb_key = build_embeddings_object_key(document_id, version_id)
    chunks_bytes = read_object_bytes(
        client=gcs_client, bucket_name=bucket_name, object_key=chunks_key
    )
    emb_bytes = read_object_bytes(
        client=gcs_client, bucket_name=bucket_name, object_key=emb_key
    )
    return join_chunks_and_embeddings(
        parse_jsonl_bytes(chunks_bytes),
        parse_jsonl_bytes(emb_bytes),
    )


def upsert_inactive_after_embed(
    *,
    settings: Settings,
    gcs_client: storage.Client,
    fs_client: firestore.Client,
    document_id: str,
    version_id: str,
    collection: str | None,
    title: str | None,
    filename: str | None,
    items: list | None = None,
    index_client: VectorIndexClient | None = None,
) -> str:
    """
    After embeddings_status=ready: upsert datapoints with active=false.

    Returns vector_status string: upserted | skipped | failed
    """
    if not _vector_configured(settings) and index_client is None:
        update_version_vector_status(
            fs_client,
            document_id=document_id,
            version_id=version_id,
            vector_status="skipped",
            vector_error="Vector Search not configured",
        )
        return "skipped"

    try:
        if items is None:
            items = load_version_chunk_embeddings(
                gcs_client=gcs_client,
                bucket_name=settings.gcs_docs_bucket,
                document_id=document_id,
                version_id=version_id,
            )
        client = index_client or _make_client(settings)
        result = upsert_version_vectors(
            client=client,
            document_id=document_id,
            version_id=version_id,
            items=items,
            active=False,
            collection=collection,
            title=title,
            filename=filename,
            index_id=settings.vector_search_index_id,
        )
        update_version_vector_status(
            fs_client,
            document_id=document_id,
            version_id=version_id,
            vector_status="upserted",
            vector_datapoint_count=result.datapoint_count,
        )
        return "upserted"
    except Exception as exc:  # noqa: BLE001
        msg = str(exc) if not isinstance(exc, VectorSearchError) else exc.message
        logger.exception(
            "vector_upsert_failed document_id=%s version_id=%s",
            document_id,
            version_id,
        )
        try:
            update_version_vector_status(
                fs_client,
                document_id=document_id,
                version_id=version_id,
                vector_status="failed",
                vector_error=msg,
            )
        except Exception:  # noqa: BLE001
            logger.exception("firestore_vector_status_update_failed")
        return "failed"


def activate_version_vectors(
    *,
    settings: Settings,
    gcs_client: storage.Client,
    fs_client: firestore.Client,
    document_id: str,
    version_id: str,
    collection: str | None = None,
    title: str | None = None,
    filename: str | None = None,
    index_client: VectorIndexClient | None = None,
) -> str:
    """Publish path: set active=true for version datapoints (no re-embed)."""
    if not _vector_configured(settings) and index_client is None:
        update_version_vector_status(
            fs_client,
            document_id=document_id,
            version_id=version_id,
            vector_status="skipped",
            vector_error="Vector Search not configured",
        )
        return "skipped"

    try:
        items = load_version_chunk_embeddings(
            gcs_client=gcs_client,
            bucket_name=settings.gcs_docs_bucket,
            document_id=document_id,
            version_id=version_id,
        )
        # Prefer metadata from version doc when available
        client = index_client or _make_client(settings)
        result = set_active_for_version(
            client=client,
            document_id=document_id,
            version_id=version_id,
            items=items,
            active=True,
            collection=collection,
            title=title,
            filename=filename,
            index_id=settings.vector_search_index_id,
        )
        update_version_vector_status(
            fs_client,
            document_id=document_id,
            version_id=version_id,
            vector_status="activated",
            vector_datapoint_count=result.datapoint_count,
        )
        return "activated"
    except Exception as exc:  # noqa: BLE001
        msg = str(exc) if not isinstance(exc, VectorSearchError) else exc.message
        logger.exception(
            "vector_activate_failed document_id=%s version_id=%s",
            document_id,
            version_id,
        )
        try:
            update_version_vector_status(
                fs_client,
                document_id=document_id,
                version_id=version_id,
                vector_status="failed",
                vector_error=msg,
            )
        except Exception:  # noqa: BLE001
            logger.exception("firestore_vector_status_update_failed")
        return "failed"


def deactivate_version_vectors(
    *,
    settings: Settings,
    gcs_client: storage.Client,
    fs_client: firestore.Client,
    document_id: str,
    version_id: str,
    collection: str | None = None,
    title: str | None = None,
    filename: str | None = None,
    index_client: VectorIndexClient | None = None,
) -> str:
    """Retire / supersede path: set active=false (no hard-delete)."""
    if not _vector_configured(settings) and index_client is None:
        update_version_vector_status(
            fs_client,
            document_id=document_id,
            version_id=version_id,
            vector_status="skipped",
            vector_error="Vector Search not configured",
        )
        return "skipped"

    try:
        items = load_version_chunk_embeddings(
            gcs_client=gcs_client,
            bucket_name=settings.gcs_docs_bucket,
            document_id=document_id,
            version_id=version_id,
        )
        client = index_client or _make_client(settings)
        result = set_active_for_version(
            client=client,
            document_id=document_id,
            version_id=version_id,
            items=items,
            active=False,
            collection=collection,
            title=title,
            filename=filename,
            index_id=settings.vector_search_index_id,
        )
        update_version_vector_status(
            fs_client,
            document_id=document_id,
            version_id=version_id,
            vector_status="deactivated",
            vector_datapoint_count=result.datapoint_count,
        )
        return "deactivated"
    except Exception as exc:  # noqa: BLE001
        msg = str(exc) if not isinstance(exc, VectorSearchError) else exc.message
        logger.exception(
            "vector_deactivate_failed document_id=%s version_id=%s",
            document_id,
            version_id,
        )
        try:
            update_version_vector_status(
                fs_client,
                document_id=document_id,
                version_id=version_id,
                vector_status="failed",
                vector_error=msg,
            )
        except Exception:  # noqa: BLE001
            logger.exception("firestore_vector_status_update_failed")
        return "failed"


def version_meta_from_firestore(
    fs_client: firestore.Client, document_id: str, version_id: str
) -> dict[str, Any]:
    """Load version fields useful for vector metadata (best-effort)."""
    from app.services.firestore_repo import version_ref

    snap = version_ref(fs_client, document_id, version_id).get()
    if not snap.exists:
        return {}
    return snap.to_dict() or {}
