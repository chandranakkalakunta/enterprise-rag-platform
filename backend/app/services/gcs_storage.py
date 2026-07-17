"""GCS write helpers for document raw uploads (Phase 2.1)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Protocol

from google.cloud import storage

logger = logging.getLogger("erp.api.gcs")

# Safe object name: strip path separators and control chars; keep extension.
_UNSAFE_FILENAME = re.compile(r"[^\w.\- ()\[\]]+", re.UNICODE)
_MAX_FILENAME_LEN = 200


class StorageClient(Protocol):
    """Minimal protocol so tests can inject a fake client."""

    def bucket(self, name: str) -> object: ...


@dataclass(frozen=True, slots=True)
class GcsUploadResult:
    bucket: str
    object_key: str
    gcs_uri: str
    size_bytes: int
    content_type: str
    filename: str


def sanitize_filename(original: str | None) -> str:
    """Return a path-safe basename for GCS object keys."""
    name = (original or "upload.bin").strip().replace("\\", "/")
    name = name.split("/")[-1] or "upload.bin"
    name = _UNSAFE_FILENAME.sub("_", name).strip("._ ") or "upload.bin"
    if len(name) > _MAX_FILENAME_LEN:
        # Preserve extension when truncating
        if "." in name:
            stem, ext = name.rsplit(".", 1)
            ext = ext[:20]
            stem = stem[: max(1, _MAX_FILENAME_LEN - len(ext) - 1)]
            name = f"{stem}.{ext}"
        else:
            name = name[:_MAX_FILENAME_LEN]
    return name


def build_raw_object_key(
    document_id: str, version_id: str, filename: str
) -> str:
    """raw/{document_id}/{version_id}/{safe_filename}."""
    safe = sanitize_filename(filename)
    return f"raw/{document_id}/{version_id}/{safe}"


def upload_raw_bytes(
    *,
    client: storage.Client,
    bucket_name: str,
    document_id: str,
    version_id: str,
    filename: str,
    data: bytes,
    content_type: str,
) -> GcsUploadResult:
    """Write upload bytes to the raw/ prefix. Returns gs:// URI metadata."""
    object_key = build_raw_object_key(document_id, version_id, filename)
    safe_name = sanitize_filename(filename)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_key)
    blob.upload_from_string(data, content_type=content_type)
    gcs_uri = f"gs://{bucket_name}/{object_key}"
    logger.info(
        "gcs_upload_ok bucket=%s key=%s size_bytes=%s",
        bucket_name,
        object_key,
        len(data),
    )
    return GcsUploadResult(
        bucket=bucket_name,
        object_key=object_key,
        gcs_uri=gcs_uri,
        size_bytes=len(data),
        content_type=content_type,
        filename=safe_name,
    )
