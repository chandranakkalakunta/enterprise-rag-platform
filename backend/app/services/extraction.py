"""Text extraction for uploaded documents (Phase 2.2).

Isolated from FastAPI / GCS / Firestore so this module can move to the
ingest-worker later without rewriting the core extractors.

Supported:
  - Markdown (text/markdown, text/x-markdown) → plain UTF-8 text
  - PDF (application/pdf) → text via pdfminer.six
"""

from __future__ import annotations

import re
from io import BytesIO

from pdfminer.high_level import extract_text as pdfminer_extract_text

# Soft cap before callers truncate for Firestore (1 MiB doc limit).
DEFAULT_MAX_CHARS = 400_000

_MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MARKDOWN_CODE_FENCE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_MARKDOWN_INLINE_CODE = re.compile(r"`([^`]+)`")
_MARKDOWN_EMPHASIS = re.compile(r"(\*\*|__|\*|_)(.*?)\1")
_MULTI_BLANK = re.compile(r"\n{3,}")


class ExtractionError(Exception):
    """Raised when text cannot be extracted from the payload."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def extract_text_from_markdown(data: bytes) -> str:
    """Decode Markdown bytes to plain-ish text (light markup stripping)."""
    if not data:
        raise ExtractionError("Empty Markdown payload")
    try:
        raw = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExtractionError(f"Markdown is not valid UTF-8: {exc}") from exc

    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = _MARKDOWN_CODE_FENCE.sub(
        lambda m: m.group(0).strip("`").strip() or "", text
    )
    text = _MARKDOWN_IMAGE.sub("", text)
    text = _MARKDOWN_LINK.sub(r"\1", text)
    text = _MARKDOWN_HEADING.sub("", text)
    text = _MARKDOWN_INLINE_CODE.sub(r"\1", text)
    text = _MARKDOWN_EMPHASIS.sub(r"\2", text)
    text = _MULTI_BLANK.sub("\n\n", text)
    text = text.strip()
    if not text:
        raise ExtractionError("No text content found in Markdown")
    return text


def extract_text_from_pdf(data: bytes) -> str:
    """Extract text from PDF bytes using pdfminer.six."""
    if not data:
        raise ExtractionError("Empty PDF payload")
    if not data.startswith(b"%PDF"):
        # Soft check — pdfminer may still fail; give a clearer message
        raise ExtractionError("Payload does not look like a PDF (%PDF header missing)")

    try:
        text = pdfminer_extract_text(BytesIO(data))
    except Exception as exc:  # noqa: BLE001 — library raises varied types
        raise ExtractionError(f"PDF extraction failed: {exc}") from exc

    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = _MULTI_BLANK.sub("\n\n", text).strip()
    if not text:
        raise ExtractionError("No text content extracted from PDF")
    return text


def extract_text(content_type: str, data: bytes) -> str:
    """
    Dispatch extraction by content type.

    Args:
        content_type: Normalized MIME type (no parameters).
        data: Raw file bytes.

    Returns:
        Extracted plain text (non-empty).

    Raises:
        ExtractionError: Unsupported type or extraction failure.
    """
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in ("text/markdown", "text/x-markdown"):
        return extract_text_from_markdown(data)
    if ct == "application/pdf":
        return extract_text_from_pdf(data)
    raise ExtractionError(f"Unsupported content type for extraction: {ct or '(empty)'}")


def truncate_extracted_text(
    text: str, max_chars: int = DEFAULT_MAX_CHARS
) -> tuple[str, int, bool]:
    """
    Cap extracted text length for Firestore document size safety.

    Returns:
        (possibly_truncated_text, full_char_count, was_truncated)
    """
    full_len = len(text)
    if full_len <= max_chars:
        return text, full_len, False
    return text[:max_chars], full_len, True
