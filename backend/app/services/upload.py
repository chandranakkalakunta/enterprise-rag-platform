"""Document upload orchestration (Phase 2.3–3.1).

Flow: validate → GCS raw/ → Firestore processing → extract → chunk →
GCS processed/ (full.txt + chunks.jsonl) → Firestore ready|failed →
embed chunks → embeddings.jsonl → embeddings_status ready|failed.

Content status (ready) is independent of embeddings_status (ADR-0007).
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
    Chunk,
    ChunkingError,
    chunk_text,
    text_preview,
)
from app.services.embeddings import (
    EmbeddingError,
    TextEmbedder,
    build_embedding_records,
    embed_texts,
)
from app.services.extraction import ExtractionError, extract_text
from app.services.firestore_repo import (
    create_document_with_version,
    update_version_embeddings_failed,
    update_version_embeddings_ready,
    update_version_failed,
    update_version_ready,
)
from app.services.gcs_storage import (
    GcsUploadResult,
    ProcessedArtifacts,
    upload_raw_bytes,
    write_embeddings_jsonl,
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
    embeddings_status: str | None = None  # ready | failed | None
    embedding_model_id: str | None = None
    embedded_chunk_count: int | None = None
    embeddings_gcs_uri: str | None = None
    embeddings_error: str | None = None


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


def _embed_and_store(
    *,
    settings: Settings,
    gcs_client: storage.Client,
    fs_client: firestore.Client,
    document_id: str,
    version_id: str,
    chunks: list[Chunk],
    embedder: TextEmbedder | None = None,
) -> tuple[str, str | None, int | None, str | None, str | None]:
    """
    Embed chunks and write embeddings.jsonl.

    Returns:
        (embeddings_status, model_id, embedded_count, gcs_uri, error)
    """
    model_id = settings.embedding_model_id
    try:
        texts = [c.text for c in chunks]
        vectors = embed_texts(
            texts,
            model_id=model_id,
            project_id=settings.gcp_project_id,
            location=settings.vertex_location,
            batch_size=settings.embedding_batch_size,
            embedder=embedder,
        )
        records = build_embedding_records(
            chunks=chunks,
            vectors=vectors,
            document_id=document_id,
            version_id=version_id,
        )
        artifact = write_embeddings_jsonl(
            client=gcs_client,
            bucket_name=settings.gcs_docs_bucket,
            document_id=document_id,
            version_id=version_id,
            records=records,
            embedding_model_id=model_id,
        )
        update_version_embeddings_ready(
            fs_client,
            document_id=document_id,
            version_id=version_id,
            embedding_model_id=model_id,
            embedded_chunk_count=artifact.embedded_chunk_count,
            embeddings_gcs_uri=artifact.gcs_uri,
        )
        return (
            "ready",
            model_id,
            artifact.embedded_chunk_count,
            artifact.gcs_uri,
            None,
        )
    except EmbeddingError as exc:
        logger.warning(
            "embeddings_failed document_id=%s version_id=%s error=%s",
            document_id,
            version_id,
            exc.message,
        )
        try:
            update_version_embeddings_failed(
                fs_client,
                document_id=document_id,
                version_id=version_id,
                embedding_model_id=model_id,
                error_message=exc.message,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "firestore_embeddings_failed_update document_id=%s version_id=%s",
                document_id,
                version_id,
            )
        return "failed", model_id, 0, None, exc.message
    except Exception as exc:  # noqa: BLE001
        msg = f"Unexpected embedding error: {exc}"
        logger.exception(
            "embeddings_unexpected document_id=%s version_id=%s",
            document_id,
            version_id,
        )
        try:
            update_version_embeddings_failed(
                fs_client,
                document_id=document_id,
                version_id=version_id,
                embedding_model_id=model_id,
                error_message=msg,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "firestore_embeddings_failed_update document_id=%s version_id=%s",
                document_id,
                version_id,
            )
        return "failed", model_id, 0, None, msg


def _run_extract_chunk_store(
    *,
    settings: Settings,
    gcs_client: storage.Client,
    fs_client: firestore.Client,
    bucket_name: str,
    document_id: str,
    version_id: str,
    content_type: str,
    data: bytes,
    chunk_target_size: int = DEFAULT_TARGET_SIZE,
    chunk_overlap: int = DEFAULT_OVERLAP,
    embedder: TextEmbedder | None = None,
) -> tuple[
    str,
    int | None,
    int | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    int | None,
    str | None,
    str | None,
]:
    """
    Extract → chunk → processed/ → ready → embed → embeddings.jsonl.

    Returns:
        (status, extracted_char_count, chunk_count, processed_prefix, preview,
         error_message, embeddings_status, embedding_model_id,
         embedded_chunk_count, embeddings_gcs_uri, embeddings_error)
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
        return status, 0, 0, None, None, err, None, None, None, None, None
    except Exception as exc:  # noqa: BLE001
        msg = f"Unexpected extraction error: {exc}"
        logger.exception(
            "extraction_unexpected document_id=%s version_id=%s",
            document_id,
            version_id,
        )
        status, _, _, _, err = _mark_failed(fs_client, document_id, version_id, msg)
        return status, 0, 0, None, None, err, None, None, None, None, None

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
        return status, len(text), 0, None, None, err, None, None, None, None, None

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
        return status, len(text), 0, None, None, err, None, None, None, None, None

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

    emb_status, emb_model, emb_count, emb_uri, emb_err = _embed_and_store(
        settings=settings,
        gcs_client=gcs_client,
        fs_client=fs_client,
        document_id=document_id,
        version_id=version_id,
        chunks=list(chunks),
        embedder=embedder,
    )

    return (
        "ready",
        artifacts.full_text_char_count,
        artifacts.chunk_count,
        artifacts.prefix,
        preview,
        None,
        emb_status,
        emb_model,
        emb_count,
        emb_uri,
        emb_err,
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
    embedder: TextEmbedder | None = None,
) -> UploadResult:
    """
    Validate → GCS raw/ → extract/chunk/processed → ready → embeddings.
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
        emb_status,
        emb_model,
        emb_count,
        emb_uri,
        emb_err,
    ) = _run_extract_chunk_store(
        settings=settings,
        gcs_client=gcs_client,
        fs_client=fs_client,
        bucket_name=settings.gcs_docs_bucket,
        document_id=document_id,
        version_id=version_id,
        content_type=validated_type,
        data=data,
        embedder=embedder,
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
        embeddings_status=emb_status,
        embedding_model_id=emb_model,
        embedded_chunk_count=emb_count,
        embeddings_gcs_uri=emb_uri,
        embeddings_error=emb_err,
    )
