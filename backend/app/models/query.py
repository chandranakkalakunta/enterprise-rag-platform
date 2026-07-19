"""Pydantic models for dense search API (Phase 3.3)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """POST /api/v1/query/search body."""

    query: str = Field(..., min_length=1, description="Natural-language search query")
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description="Override RETRIEVAL_TOP_K (default 5)",
    )
    collection: str | None = Field(
        default=None,
        description="Optional collection filter (restrict namespace collection)",
    )


class SearchHit(BaseModel):
    """One ranked chunk from Vector Search."""

    text: str | None = None
    score: float
    document_id: str | None = None
    version_id: str | None = None
    chunk_index: int | None = None
    title: str | None = None
    filename: str | None = None
    collection: str | None = None
    datapoint_id: str
    char_count: int | None = None


class SearchResponseBody(BaseModel):
    """Dense search response (no generation)."""

    query: str
    top_k: int
    results: list[SearchHit]
