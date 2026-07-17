"""Text chunking for RAG ingestion (Phase 2.3).

Pure functions — no FastAPI / GCS / Firestore dependencies.
Defaults: ~1000 characters, 150 overlap; prefer paragraph then sentence boundaries.

Future tuning (size, overlap, separators, evaluation) tracked in backlog.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_TARGET_SIZE = 1000
DEFAULT_OVERLAP = 150
TEXT_PREVIEW_CHARS = 500

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


@dataclass(frozen=True, slots=True)
class Chunk:
    """One chunk of extracted document text."""

    index: int
    text: str
    char_count: int
    start_offset: int
    end_offset: int

    @property
    def chunk_id(self) -> str:
        return str(self.index)

    def to_jsonl_dict(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "index": self.index,
            "text": self.text,
            "char_count": self.char_count,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }


class ChunkingError(Exception):
    """Raised when chunking cannot produce a valid chunk list."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def text_preview(text: str, max_chars: int = TEXT_PREVIEW_CHARS) -> str:
    """First N characters for Firestore metadata (not the full document)."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _find_split_point(window: str, target_size: int) -> int:
    """
    Choose a split index within window preferably at paragraph or sentence boundary.

    Returns index into ``window`` (1..len) where the chunk should end.
    Always returns at least 1 if window is non-empty.
    """
    if len(window) <= target_size:
        return len(window)

    hard = target_size
    search = window[:hard]

    # Prefer last paragraph break in the window
    paras = list(_PARAGRAPH_SPLIT.finditer(search))
    if paras:
        # End after the paragraph separator
        end = paras[-1].end()
        if end >= max(target_size // 3, 1):
            return end

    # Prefer last sentence boundary in the latter half of the window
    best_sentence = -1
    for m in _SENTENCE_BOUNDARY.finditer(search):
        if m.start() >= target_size // 3:
            best_sentence = m.start()
    if best_sentence > 0:
        return best_sentence

    # Prefer last whitespace
    ws = search.rfind(" ")
    if ws >= target_size // 3:
        return ws + 1

    return hard


def chunk_text(
    text: str,
    target_size: int = DEFAULT_TARGET_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """
    Split text into overlapping chunks.

    Args:
        text: Full extracted plain text.
        target_size: Approximate max characters per chunk (default 1000).
        overlap: Characters of previous chunk to re-include (default 150).

    Returns:
        Ordered list of Chunk objects with absolute offsets into ``text``.
    """
    if target_size < 1:
        raise ChunkingError("target_size must be >= 1")
    if overlap < 0:
        raise ChunkingError("overlap must be >= 0")
    if overlap >= target_size:
        raise ChunkingError("overlap must be < target_size")

    if text is None:
        raise ChunkingError("text is required")

    # Normalize newlines; preserve content
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.strip():
        raise ChunkingError("Cannot chunk empty text")

    n = len(normalized)
    if n <= target_size:
        return [
            Chunk(
                index=0,
                text=normalized,
                char_count=n,
                start_offset=0,
                end_offset=n,
            )
        ]

    chunks: list[Chunk] = []
    start = 0
    index = 0

    while start < n:
        window = normalized[start:]
        split_rel = _find_split_point(window, target_size)
        end = start + split_rel
        if end <= start:
            end = min(start + target_size, n)

        piece = normalized[start:end]
        if not piece:
            break

        chunks.append(
            Chunk(
                index=index,
                text=piece,
                char_count=len(piece),
                start_offset=start,
                end_offset=end,
            )
        )
        index += 1

        if end >= n:
            break

        # Advance with overlap; always move forward at least 1 character
        next_start = end - overlap
        if next_start <= start:
            next_start = start + max(1, target_size - overlap)
        start = min(next_start, n)

    if not chunks:
        raise ChunkingError("Chunking produced no chunks")

    return chunks
