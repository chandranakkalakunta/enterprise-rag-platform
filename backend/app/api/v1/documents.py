"""Document upload API — Phase 2.1."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.auth import AuthContext, require_upload_auth
from app.core.config import Settings, get_settings
from app.models.documents import UploadResponse
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
    Accept multipart upload, write to GCS `raw/`, create Firestore Document + Version.

    Initial version status is always `processing`. Parsing/chunking is not run yet.
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
        "upload_ok document_id=%s version_id=%s size_bytes=%s auth_mode=%s",
        result.document_id,
        result.version_id,
        result.size_bytes,
        auth.auth_mode,
    )

    return UploadResponse(
        document_id=result.document_id,
        version_id=result.version_id,
        status="processing",
        gcs_uri=result.gcs_uri,
        filename=result.filename,
        content_type=result.content_type,
        size_bytes=result.size_bytes,
        title=result.title,
        collection=result.collection,
    )
