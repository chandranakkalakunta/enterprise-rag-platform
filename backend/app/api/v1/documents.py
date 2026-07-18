"""Document upload + version lifecycle API (Phase 2.1–2.4)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from google.cloud import firestore

from app.core.auth import AuthContext, require_content_auth, require_upload_auth
from app.core.config import Settings, get_settings
from app.models.documents import UploadResponse, VersionLifecycleResponse
from app.services.lifecycle import (
    ConflictError,
    InvalidIdError,
    LifecycleResult,
    NotFoundError,
    publish_version,
    retire_version,
)
from app.services.upload import (
    UploadStorageError,
    UploadValidationError,
    process_upload,
)

logger = logging.getLogger("erp.api.documents")

router = APIRouter(prefix="/documents", tags=["documents"])

_READ_CHUNK = 1024 * 1024


async def _read_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """Read upload stream with hard size cap."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(_READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise UploadValidationError(
                f"File too large: exceeds limit of {max_bytes} bytes"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _lifecycle_http(exc: Exception) -> HTTPException:
    if isinstance(exc, InvalidIdError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        )
    if isinstance(exc, NotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.message
        )
    if isinstance(exc, ConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=exc.message
        )
    logger.exception("lifecycle_unexpected")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Lifecycle operation failed",
    )


def _to_lifecycle_response(result: LifecycleResult) -> VersionLifecycleResponse:
    return VersionLifecycleResponse(
        document_id=result.document_id,
        version_id=result.version_id,
        status=result.status,  # type: ignore[arg-type]
        active_version_id=result.active_version_id,
        published_at=result.published_at,
        published_by=result.published_by,
        retired_at=result.retired_at,
        retired_by=result.retired_by,
        previous_published_version_id=result.previous_published_version_id,
        cleared_active_pointer=result.cleared_active_pointer,
    )


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document (PDF or Markdown)",
    responses={
        400: {"description": "Unsupported media type or file too large / empty"},
        401: {"description": "Missing or invalid Bearer token (when bypass off)"},
        500: {"description": "GCS or Firestore failure"},
    },
)
async def upload_document(
    auth: Annotated[AuthContext, Depends(require_upload_auth)],
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File(description="PDF or Markdown file")],
    title: Annotated[str | None, Form()] = None,
    collection: Annotated[str | None, Form()] = None,
) -> UploadResponse:
    """
    Upload → extract → chunk → processed/ → ready → embed → embeddings.jsonl.

    Content status ready is independent of embeddings_status (ADR-0007).
    """
    try:
        data = await _read_limited(file, settings.max_upload_bytes)
        result = process_upload(
            settings=settings,
            data=data,
            filename=file.filename,
            content_type=file.content_type,
            title=title,
            collection=collection,
            created_by=auth.subject,
        )
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc
    except UploadStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message,
        ) from exc

    logger.info(
        "upload_ok document_id=%s version_id=%s status=%s chunks=%s auth_mode=%s",
        result.document_id,
        result.version_id,
        result.status,
        result.chunk_count,
        auth.auth_mode,
    )

    return UploadResponse(
        document_id=result.document_id,
        version_id=result.version_id,
        status=result.status,  # type: ignore[arg-type]
        gcs_uri=result.gcs_uri,
        filename=result.filename,
        content_type=result.content_type,
        size_bytes=result.size_bytes,
        title=result.title,
        collection=result.collection,
        extracted_char_count=result.extracted_char_count,
        chunk_count=result.chunk_count,
        processed_gcs_prefix=result.processed_gcs_prefix,
        text_preview=result.text_preview,
        error_message=result.error_message,
        embeddings_status=result.embeddings_status,  # type: ignore[arg-type]
        embedding_model_id=result.embedding_model_id,
        embedded_chunk_count=result.embedded_chunk_count,
        embeddings_gcs_uri=result.embeddings_gcs_uri,
        embeddings_error=result.embeddings_error,
        vector_status=result.vector_status,
    )


@router.post(
    "/{document_id}/versions/{version_id}/publish",
    response_model=VersionLifecycleResponse,
    summary="Publish a ready version (retires previous published)",
    responses={
        400: {"description": "Malformed document_id or version_id"},
        401: {"description": "Unauthorized"},
        404: {"description": "Document or version not found"},
        409: {"description": "Illegal state transition"},
        500: {"description": "Firestore failure"},
    },
)
async def publish_document_version(
    document_id: str,
    version_id: str,
    auth: Annotated[AuthContext, Depends(require_content_auth)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VersionLifecycleResponse:
    """
    Transition version ready → published and set document.active_version_id.

    If another version was published (active), it is set to retired atomically.
    Temporary auth only — content_admin role check comes later.
    """
    try:
        client = firestore.Client(project=settings.gcp_project_id)
        result = publish_version(
            client,
            document_id=document_id,
            version_id=version_id,
            actor=auth.subject,
        )
        # Vector Search: activate published version; deactivate previous (no re-embed)
        from google.cloud import storage as gcs_storage

        from app.services.vector_ops import (
            activate_version_vectors,
            deactivate_version_vectors,
            version_meta_from_firestore,
        )

        gcs_client = gcs_storage.Client(project=settings.gcp_project_id)
        doc_snap = client.collection("documents").document(document_id).get()
        doc_data = doc_snap.to_dict() or {} if doc_snap.exists else {}
        meta = version_meta_from_firestore(client, document_id, version_id)
        activate_version_vectors(
            settings=settings,
            gcs_client=gcs_client,
            fs_client=client,
            document_id=document_id,
            version_id=version_id,
            collection=doc_data.get("collection"),
            title=doc_data.get("title"),
            filename=meta.get("filename"),
        )
        if result.previous_published_version_id:
            prev_meta = version_meta_from_firestore(
                client, document_id, result.previous_published_version_id
            )
            deactivate_version_vectors(
                settings=settings,
                gcs_client=gcs_client,
                fs_client=client,
                document_id=document_id,
                version_id=result.previous_published_version_id,
                collection=doc_data.get("collection"),
                title=doc_data.get("title"),
                filename=prev_meta.get("filename"),
            )
    except (InvalidIdError, NotFoundError, ConflictError) as exc:
        raise _lifecycle_http(exc) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "publish_failed document_id=%s version_id=%s", document_id, version_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish version",
        ) from exc

    return _to_lifecycle_response(result)


@router.post(
    "/{document_id}/versions/{version_id}/retire",
    response_model=VersionLifecycleResponse,
    summary="Retire a ready or published version",
    responses={
        400: {"description": "Malformed document_id or version_id"},
        401: {"description": "Unauthorized"},
        404: {"description": "Document or version not found"},
        409: {"description": "Illegal state transition"},
        500: {"description": "Firestore failure"},
    },
)
async def retire_document_version(
    document_id: str,
    version_id: str,
    auth: Annotated[AuthContext, Depends(require_content_auth)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VersionLifecycleResponse:
    """
    Transition version ready|published → retired. History is retained.

    Clears document.active_version_id when retiring the active version.
    """
    try:
        client = firestore.Client(project=settings.gcp_project_id)
        result = retire_version(
            client,
            document_id=document_id,
            version_id=version_id,
            actor=auth.subject,
        )
        from google.cloud import storage as gcs_storage

        from app.services.vector_ops import (
            deactivate_version_vectors,
            version_meta_from_firestore,
        )

        gcs_client = gcs_storage.Client(project=settings.gcp_project_id)
        doc_snap = client.collection("documents").document(document_id).get()
        doc_data = doc_snap.to_dict() or {} if doc_snap.exists else {}
        meta = version_meta_from_firestore(client, document_id, version_id)
        deactivate_version_vectors(
            settings=settings,
            gcs_client=gcs_client,
            fs_client=client,
            document_id=document_id,
            version_id=version_id,
            collection=doc_data.get("collection"),
            title=doc_data.get("title"),
            filename=meta.get("filename"),
        )
    except (InvalidIdError, NotFoundError, ConflictError) as exc:
        raise _lifecycle_http(exc) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "retire_failed document_id=%s version_id=%s", document_id, version_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retire version",
        ) from exc

    return _to_lifecycle_response(result)
