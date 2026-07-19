"""Pydantic models for document upload and version lifecycle (Phase 2.1–2.4)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

VersionStatus = Literal[
    "processing", "ready", "failed", "published", "retired"
]


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
    embeddings_status: Literal["ready", "failed"] | None = Field(
        default=None,
        description="Separate from content status (Phase 3.1)",
    )
    embedding_model_id: str | None = None
    embedded_chunk_count: int | None = None
    embeddings_gcs_uri: str | None = None
    embeddings_error: str | None = None
    vector_status: str | None = Field(
        default=None,
        description="Vector Search: upserted | skipped | failed (Phase 3.2)",
    )


class VersionLifecycleResponse(BaseModel):
    """Response for publish / retire endpoints."""

    document_id: str
    version_id: str
    status: Literal["published", "retired"]
    active_version_id: str | None = Field(
        default=None,
        description="Document active (published) version pointer after the operation",
    )
    published_at: datetime | None = None
    published_by: str | None = None
    retired_at: datetime | None = None
    retired_by: str | None = None
    previous_published_version_id: str | None = Field(
        default=None,
        description="Set on publish when a prior published version was retired",
    )
    cleared_active_pointer: bool = Field(
        default=False,
        description="True on retire when this version was the active pointer",
    )


class ErrorBody(BaseModel):
    """Stable error envelope for client handling."""

    detail: str


class VersionSummary(BaseModel):
    """Minimal version fields for Admin list/detail (Phase 5.3)."""

    version_id: str
    status: VersionStatus
    filename: str | None = None
    gcs_uri: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    created_at: datetime | None = None
    created_by: str | None = None
    chunk_count: int | None = None
    embeddings_status: str | None = None
    vector_status: str | None = None
    error_message: str | None = None
    text_preview: str | None = None


class DocumentSummary(BaseModel):
    """Document row for Admin list."""

    document_id: str
    title: str | None = None
    collection: str | None = None
    active_version_id: str | None = None
    latest_version_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None
    latest_version: VersionSummary | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]
    count: int


class DocumentDetailResponse(BaseModel):
    """Single document with all versions (Admin detail)."""

    document_id: str
    title: str | None = None
    collection: str | None = None
    active_version_id: str | None = None
    latest_version_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None
    latest_version: VersionSummary | None = None
    versions: list[VersionSummary] = Field(default_factory=list)
