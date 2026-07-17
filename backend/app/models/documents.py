"""Pydantic models for document upload (Phase 2.1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Initial version status after upload (ADR-0003: PROCESSING). No parse yet.
VersionStatus = Literal["processing"]


class UploadResponse(BaseModel):
    """201 response body for POST /api/v1/documents/upload."""

    document_id: str = Field(..., description="Stable logical document id")
    version_id: str = Field(..., description="Immutable version snapshot id")
    status: VersionStatus = Field(
        default="processing",
        description="Version lifecycle status (always processing on create)",
    )
    gcs_uri: str = Field(..., description="gs:// URI of the raw upload object")
    filename: str = Field(..., description="Sanitized original filename")
    content_type: str = Field(..., description="Validated content type")
    size_bytes: int = Field(..., ge=0, description="Object size in bytes")
    title: str | None = Field(default=None, description="Optional document title")
    collection: str | None = Field(
        default=None, description="Optional collection label"
    )


class ErrorBody(BaseModel):
    """Stable error envelope for client handling."""

    detail: str
