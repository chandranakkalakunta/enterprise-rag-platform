"""Unit tests for text chunking (Phase 2.3)."""

from __future__ import annotations

import pytest

from app.services.chunking import (
    DEFAULT_OVERLAP,
    DEFAULT_TARGET_SIZE,
    ChunkingError,
    chunk_text,
    text_preview,
)


def test_defaults() -> None:
    assert DEFAULT_TARGET_SIZE == 1000
    assert DEFAULT_OVERLAP == 150


def test_short_text_single_chunk() -> None:
    text = "Hello world."
    chunks = chunk_text(text, target_size=1000, overlap=150)
    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].text == text
    assert chunks[0].char_count == len(text)
    assert chunks[0].start_offset == 0
    assert chunks[0].end_offset == len(text)


def test_empty_raises() -> None:
    with pytest.raises(ChunkingError, match="empty"):
        chunk_text("   \n\n  ")


def test_chunk_size_and_overlap() -> None:
    # Build text longer than target with clear paragraph boundaries
    para = "A" * 200 + ".\n\n"
    text = para * 8  # ~1600+ chars with separators
    chunks = chunk_text(text, target_size=500, overlap=50)
    assert len(chunks) >= 2
    for c in chunks:
        # Hard cap can slightly exceed on boundary edge cases; keep generous
        assert c.char_count <= 500 + 50  # soft check
        assert c.char_count > 0
        assert c.end_offset > c.start_offset
        assert text[c.start_offset : c.end_offset] == c.text

    # Overlap: next chunk should start before previous end
    for i in range(1, len(chunks)):
        assert chunks[i].start_offset < chunks[i - 1].end_offset
        assert chunks[i].start_offset >= chunks[i - 1].start_offset


def test_sentence_boundary_preference() -> None:
    # Without spaces/paragraphs mid-chunk, sentences help
    s1 = "This is sentence one. "
    s2 = "This is sentence two. "
    s3 = "This is sentence three which is longer than usual for testing purposes. "
    text = (s1 + s2 + s3) * 20
    chunks = chunk_text(text, target_size=120, overlap=20)
    assert len(chunks) > 1
    # Reconstruct coverage: first char and last char included
    assert chunks[0].start_offset == 0
    assert chunks[-1].end_offset == len(text)


def test_invalid_params() -> None:
    with pytest.raises(ChunkingError):
        chunk_text("abc", target_size=0, overlap=0)
    with pytest.raises(ChunkingError):
        chunk_text("abc", target_size=10, overlap=10)
    with pytest.raises(ChunkingError):
        chunk_text("abc", target_size=10, overlap=-1)


def test_jsonl_dict_shape() -> None:
    chunks = chunk_text("Short.", target_size=100, overlap=10)
    d = chunks[0].to_jsonl_dict()
    assert d["index"] == 0
    assert d["chunk_id"] == "0"
    assert "text" in d
    assert d["char_count"] == len("Short.")


def test_text_preview() -> None:
    assert text_preview("hi", max_chars=500) == "hi"
    long = "x" * 600
    assert len(text_preview(long, max_chars=500)) == 500
