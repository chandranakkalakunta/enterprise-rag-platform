"""Document upload orchestration (Phase 2.3).

Flow: validate → GCS raw/ → Firestore processing → extract → chunk →
GCS processed/ (full.txt + chunks.jsonl) → Firestore ready|failed.

Extraction and chunking modules are worker-ready (no framework coupling).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Callable

from google.cloud import firestore, storage

from app.core.config import Settings
from app.services.chunking import (
    DEFAULT_OVERLAP,
    DEFAULT_TARGET_SIZE,
    ChunkingError,
    chunk_text,
    text_preview,
)
from app.services.extraction import ExtractionError, extract_text
from app.services.firestore_repo import (
    create_document_with_version,
    update_version_failed,
    update_version_ready,
)
from app.services.gcs_storage import (
    GcsUploadResult,
    ProcessedArtifacts,
    upload_raw_bytes,
    write_processed_artifacts,
)

logger = logging.getLogger("erp.api.upload")

ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "text/markdown",
        "text/x-markdown",
    }
)

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".md", ".markdown"})


class UploadValidationError(Exception):
    """Client-facing validation failure (maps to HTTP 400)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class UploadStorageError(Exception):
    """GCS or Firestore failure (maps to HTTP 500 with safe message)."""

    def __init__(self, message: str = "Storage operation failed") -> None:
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class UploadResult:
    document_id: str
    version_id: str
    status: str  # ready | failed
    gcs_uri: str
    filename: str
    content_type: str
    size_bytes: int
    title: str | None
    collection: str | None
    extracted_char_count: int | None = None
    chunk_count: int | None = None
    processed_gcs_prefix: str | None = None
    text_preview: str | None = None
    error_message: str | None = None


def _normalize_content_type(content_type: str | None) -> str:
    if not content_type:
        return ""
    return content_type.split(";")[0].strip().lower()


def _extension(filename: str | None) -> str:
    name = (filename or "").lower().strip()
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1]


def validate_upload(
    *,
    content_type: str | None,
    filename: str | None,
    size_bytes: int,
    max_bytes: int,
) -> str:
    """Validate type and size. Returns normalized content type to store."""
    if size_bytes <= 0:
        raise UploadValidationError("Empty file is not allowed")
    if size_bytes > max_bytes:
        raise UploadValidationError(
            f"File too large: {size_bytes} bytes exceeds limit of {max_bytes} bytes"
        )

    normalized = _normalize_content_type(content_type)
    ext = _extension(filename)

    if normalized in ALLOWED_CONTENT_TYPES:
        if ext and ext not in ALLOWED_EXTENSIONS:
            raise UploadValidationError(
                f"Unsupported file extension '{ext}' "
                f"(allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))})"
            )
        return normalized

    if normalized in ("", "application/octet-stream") and ext in ALLOWED_EXTENSIONS:
        if ext == ".pdf":
            return "application/pdf"
        return "text/markdown"

    raise UploadValidationError(
        "Unsupported media type. Accepted: application/pdf, text/markdown, "
        "text/x-markdown (PDF or Markdown only)"
    )


def new_ids() -> tuple[str, str]:
    """Generate document_id and version_id (UUID4 strings)."""
    return str(uuid.uuid4()), str(uuid.uuid4())


def _mark_failed(
    fs_client: firestore.Client,
    document_id: str,
    version_id: str,
    error_message: str,
) -> tuple[str, None, None, None, str]:
    try:
        update_version_failed(
            fs_client,
            document_id=document_id,
            version_id=version_id,
            error_message=error_message,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "firestore_failed_status_update document_id=%s version_id=%s",
            document_id,
            version_id,
        )
        raise UploadStorageError(
            "Failed to record processing failure status"
        ) from exc
    return "failed", None, None, None, error_message


def _run_extract_chunk_store(
    *,
    gcs_client: storage.Client,
    fs_client: firestore.Client,
    bucket_name: str,
    document_id: str,
    version_id: str,
    content_type: str,
    data: bytes,
    chunk_target_size: int = DEFAULT_TARGET_SIZE,
    chunk_overlap: int = DEFAULT_OVERLAP,
) -> tuple[str, int | None, int | None, str | None, str | None, str | None]:
    """
    Extract → chunk → write processed/ → update Firestore.

    Returns:
        (status, extracted_char_count, chunk_count, processed_prefix,
         preview, error_message)
    """
    try:
        text = extract_text(content_type, data)
    except ExtractionError as exc:
        logger.warning(
            "extraction_failed document_id=%s version_id=%s error=%s",
            document_id,
            version_id,
            exc.message,
        )
        status, _, _, _, err = _mark_failed(
            fs_client, document_id, version_id, exc.message
        )
        return status, 0, 0, None, None, err
    except Exception as exc:  # noqa: BLE001
        msg = f"Unexpected extraction error: {exc}"
        logger.exception(
            "extraction_unexpected document_id=%s version_id=%s",
            document_id,
            version_id,
        )
        status, _, _, _, err = _mark_failed(fs_client, document_id, version_id, msg)
        return status, 0, 0, None, None, err

    try:
        chunks = chunk_text(
            text, target_size=chunk_target_size, overlap=chunk_overlap
        )
    except ChunkingError as exc:
        logger.warning(
            "chunking_failed document_id=%s version_id=%s error=%s",
            document_id,
            version_id,
            exc.message,
        )
        status, _, _, _, err = _mark_failed(
            fs_client, document_id, version_id, exc.message
        )
        return status, len(text), 0, None, None, err

    try:
        artifacts: ProcessedArtifacts = write_processed_artifacts(
            client=gcs_client,
            bucket_name=bucket_name,
            document_id=document_id,
            version_id=version_id,
            full_text=text,
            chunks=chunks,
        )
    except Exception as exc:  # noqa: BLE001
        msg = "Failed to store processed artifacts in GCS"
        logger.exception(
            "gcs_processed_failed document_id=%s version_id=%s",
            document_id,
            version_id,
        )
        status, _, _, _, err = _mark_failed(
            fs_client, document_id, version_id, f"{msg}: {exc}"
        )
        return status, len(text), 0, None, None, err

    preview = text_preview(text)
    try:
        update_version_ready(
            fs_client,
            document_id=document_id,
            version_id=version_id,
            processed_gcs_prefix=artifacts.prefix,
            full_text_gcs_uri=artifacts.full_text_gcs_uri,
            chunks_gcs_uri=artifacts.chunks_gcs_uri,
            chunk_count=artifacts.chunk_count,
            text_preview=preview,
            extracted_char_count=artifacts.full_text_char_count,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "firestore_ready_update_failed document_id=%s version_id=%s",
            document_id,
            version_id,
        )
        raise UploadStorageError(
            "Failed to record ready status after processing"
        ) from exc

    return (
        "ready",
        artifacts.full_text_char_count,
        artifacts.chunk_count,
        artifacts.prefix,
        preview,
        None,
    )


def process_upload(
    *,
    settings: Settings,
    data: bytes,
    filename: str | None,
    content_type: str | None,
    title: str | None,
    collection: str | None,
    created_by: str,
    storage_client: storage.Client | None = None,
    firestore_client: firestore.Client | None = None,
    id_factory: Callable[[], tuple[str, str]] | None = None,
) -> UploadResult:
    """
    Validate → GCS raw/ → Firestore processing → extract/chunk/processed → ready|failed.
    """
    validated_type = validate_upload(
        content_type=content_type,
        filename=filename,
        size_bytes=len(data),
        max_bytes=settings.max_upload_bytes,
    )
    factory = id_factory or new_ids
    document_id, version_id = factory()

    gcs_client = storage_client or storage.Client(project=settings.gcp_project_id)
    try:
        gcs_result: GcsUploadResult = upload_raw_bytes(
            client=gcs_client,
            bucket_name=settings.gcs_docs_bucket,
            document_id=document_id,
            version_id=version_id,
            filename=filename or "upload.bin",
            data=data,
            content_type=validated_type,
        )
    except UploadValidationError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("gcs_upload_failed")
        raise UploadStorageError("Failed to store document in GCS") from exc

    fs_client = firestore_client or firestore.Client(project=settings.gcp_project_id)
    try:
        create_document_with_version(
            fs_client,
            document_id=document_id,
            version_id=version_id,
            title=title,
            collection=collection,
            gcs_uri=gcs_result.gcs_uri,
            gcs_object_key=gcs_result.object_key,
            filename=gcs_result.filename,
            content_type=gcs_result.content_type,
            size_bytes=gcs_result.size_bytes,
            created_by=created_by,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "firestore_write_failed document_id=%s version_id=%s",
            document_id,
            version_id,
        )
        raise UploadStorageError("Failed to record document metadata") from exc

    (
        status,
        char_count,
        chunk_count,
        processed_prefix,
        preview,
        error_message,
    ) = _run_extract_chunk_store(
        gcs_client=gcs_client,
        fs_client=fs_client,
        bucket_name=settings.gcs_docs_bucket,
        document_id=document_id,
        version_id=version_id,
        content_type=validated_type,
        data=data,
    )

    return UploadResult(
        document_id=document_id,
        version_id=version_id,
        status=status,
        gcs_uri=gcs_result.gcs_uri,
        filename=gcs_result.filename,
        content_type=gcs_result.content_type,
        size_bytes=gcs_result.size_bytes,
        title=title,
        collection=collection,
        extracted_char_count=char_count,
        chunk_count=chunk_count,
        processed_gcs_prefix=processed_prefix,
        text_preview=preview,
        error_message=error_message,
    )
