"""Document upload orchestration: validate → GCS → Firestore (Phase 2.1)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Callable

from google.cloud import firestore, storage

from app.core.config import Settings
from app.services.firestore_repo import create_document_with_version
from app.services.gcs_storage import GcsUploadResult, upload_raw_bytes

logger = logging.getLogger("erp.api.upload")

# Allowed content types (PDF + Markdown only for Phase 2.1)
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
    status: str
    gcs_uri: str
    filename: str
    content_type: str
    size_bytes: int
    title: str | None
    collection: str | None


def _normalize_content_type(content_type: str | None) -> str:
    if not content_type:
        return ""
    # Drop parameters e.g. charset
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
        # Guard against mismatched extension when provided
        if ext and ext not in ALLOWED_EXTENSIONS:
            raise UploadValidationError(
                f"Unsupported file extension '{ext}' "
                f"(allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))})"
            )
        return normalized

    # Browsers sometimes send octet-stream / empty for .md — allow only with extension
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
    Validate, write raw object to GCS, create Firestore document + version.

    Order: validate → IDs → GCS → Firestore.
    On Firestore failure after GCS write, raises UploadStorageError; orphan raw
    object may exist (cleanup deferred to later ops tooling).
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
    except Exception as exc:  # noqa: BLE001 — map to safe 500
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

    return UploadResult(
        document_id=document_id,
        version_id=version_id,
        status="processing",
        gcs_uri=gcs_result.gcs_uri,
        filename=gcs_result.filename,
        content_type=gcs_result.content_type,
        size_bytes=gcs_result.size_bytes,
        title=title,
        collection=collection,
    )
