"""Pydantic models for document upload (Phase 2.1–2.3)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

VersionStatus = Literal["processing", "ready", "failed"]


class UploadResponse(BaseModel):
    """201 response body for POST /api/v1/documents/upload."""

    document_id: str = Field(..., description="Stable logical document id")
    version_id: str = Field(..., description="Immutable version snapshot id")
    status: VersionStatus = Field(
        ...,
        description="Final version status after processing: ready or failed",
    )
    gcs_uri: str = Field(..., description="gs:// URI of the raw upload object")
    filename: str = Field(..., description="Sanitized original filename")
    content_type: str = Field(..., description="Validated content type")
    size_bytes: int = Field(..., ge=0, description="Object size in bytes")
    title: str | None = Field(default=None, description="Optional document title")
    collection: str | None = Field(
        default=None, description="Optional collection label"
    )
    extracted_char_count: int | None = Field(
        default=None,
        description="Character count of full extracted text (stored in GCS)",
    )
    chunk_count: int | None = Field(
        default=None, description="Number of chunks written to chunks.jsonl"
    )
    processed_gcs_prefix: str | None = Field(
        default=None,
        description="GCS prefix processed/{document_id}/{version_id}/",
    )
    text_preview: str | None = Field(
        default=None,
        description="First ~500 characters of extracted text (Firestore metadata)",
    )
    error_message: str | None = Field(
        default=None,
        description="Present when status=failed (safe, bounded message)",
    )


class ErrorBody(BaseModel):
    """Stable error envelope for client handling."""

    detail: str
