"""Unit tests for text extraction (Phase 2.2) — no FastAPI/GCS/Firestore deps."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.extraction import (
    ExtractionError,
    extract_text,
    extract_text_from_markdown,
    extract_text_from_pdf,
    truncate_extracted_text,
)


def test_extract_markdown_success() -> None:
    data = b"# Title\n\nHello **world** and [link](https://ex.com).\n"
    text = extract_text_from_markdown(data)
    assert "Title" in text
    assert "Hello" in text
    assert "world" in text
    assert "link" in text
    assert "https://ex.com" not in text
    assert "**" not in text


def test_extract_markdown_via_dispatch() -> None:
    text = extract_text("text/markdown", b"Simple line\n")
    assert "Simple line" in text


def test_extract_markdown_x_markdown() -> None:
    text = extract_text("text/x-markdown; charset=utf-8", b"Note body")
    assert text == "Note body"


def test_extract_markdown_empty_raises() -> None:
    with pytest.raises(ExtractionError, match="Empty"):
        extract_text_from_markdown(b"")


def test_extract_markdown_whitespace_only_raises() -> None:
    with pytest.raises(ExtractionError, match="No text"):
        extract_text_from_markdown(b"   \n\n  ")


def test_extract_pdf_success_mocked() -> None:
    fake_pdf = b"%PDF-1.4 fake"
    with patch(
        "app.services.extraction.pdfminer_extract_text",
        return_value="Page one text\n\nPage two",
    ) as mock_pdf:
        text = extract_text_from_pdf(fake_pdf)
    mock_pdf.assert_called_once()
    assert "Page one text" in text
    assert "Page two" in text


def test_extract_pdf_via_dispatch() -> None:
    with patch(
        "app.services.extraction.pdfminer_extract_text",
        return_value="from dispatch",
    ):
        assert extract_text("application/pdf", b"%PDF-1.4 x") == "from dispatch"


def test_extract_pdf_missing_header() -> None:
    with pytest.raises(ExtractionError, match="PDF header"):
        extract_text_from_pdf(b"not a pdf")


def test_extract_pdf_empty_text() -> None:
    with patch(
        "app.services.extraction.pdfminer_extract_text",
        return_value="   \n",
    ):
        with pytest.raises(ExtractionError, match="No text"):
            extract_text_from_pdf(b"%PDF-1.4 empty")


def test_extract_pdf_library_error() -> None:
    with patch(
        "app.services.extraction.pdfminer_extract_text",
        side_effect=ValueError("corrupt"),
    ):
        with pytest.raises(ExtractionError, match="PDF extraction failed"):
            extract_text_from_pdf(b"%PDF-1.4 x")


def test_extract_unsupported_type() -> None:
    with pytest.raises(ExtractionError, match="Unsupported"):
        extract_text("application/msword", b"x")


def test_truncate_under_limit() -> None:
    stored, count, truncated = truncate_extracted_text("hello", max_chars=100)
    assert stored == "hello"
    assert count == 5
    assert truncated is False


def test_truncate_over_limit() -> None:
    stored, count, truncated = truncate_extracted_text("abcdefghij", max_chars=4)
    assert stored == "abcd"
    assert count == 10
    assert truncated is True
