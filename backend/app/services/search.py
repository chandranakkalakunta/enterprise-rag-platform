"""Dense search orchestration (Phase 3.3 / ADR-0008) — no generation.

Hybrid entrypoint: ``app.services.hybrid_search.hybrid_search`` (Phase 4.2).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.config import Settings
from app.services.embeddings import EmbeddingError, TextEmbedder, embed_texts
from app.services.vector_search import (
    NeighborHit,
    VectorQueryClient,
    VectorSearchError,
    VertexMatchClient,
    find_neighbors,
)

logger = logging.getLogger("erp.api.search")


class SearchValidationError(Exception):
    """Client validation failure (HTTP 400)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class SearchServiceError(Exception):
    """Search backend failure (HTTP 503/500)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class SearchResultItem:
    text: str | None
    score: float
    document_id: str | None
    version_id: str | None
    chunk_index: int | None
    title: str | None
    filename: str | None
    collection: str | None
    datapoint_id: str
    char_count: int | None = None


@dataclass(frozen=True, slots=True)
class SearchResponse:
    query: str
    top_k: int
    results: list[SearchResultItem]


def _match_client(settings: Settings) -> VertexMatchClient:
    if not settings.vector_search_enabled:
        raise SearchServiceError("Vector Search is not enabled (VECTOR_SEARCH_ENABLED)")
    if not (settings.vector_search_endpoint_id or "").strip():
        raise SearchServiceError("VECTOR_SEARCH_ENDPOINT_ID is not configured")
    if not (settings.vector_search_deployed_index_id or "").strip():
        raise SearchServiceError("VECTOR_SEARCH_DEPLOYED_INDEX_ID is not configured")
    return VertexMatchClient(
        project_id=settings.gcp_project_id,
        location=settings.vector_search_region,
        endpoint_id=settings.vector_search_endpoint_id.strip(),
        deployed_index_id=settings.vector_search_deployed_index_id.strip(),
        public_endpoint_domain=settings.vector_search_public_endpoint_domain,
    )


def dense_search(
    *,
    settings: Settings,
    query: str,
    top_k: int | None = None,
    collection: str | None = None,
    embedder: TextEmbedder | None = None,
    query_client: VectorQueryClient | None = None,
) -> SearchResponse:
    """
    Embed query → Vector Search FindNeighbors (active=true only).

    No generation; returns ranked chunks for citations / later grounding.
    """
    q = (query or "").strip()
    if not q:
        raise SearchValidationError("query must be a non-empty string")

    k = top_k if top_k is not None else settings.retrieval_top_k
    if k < 1 or k > 50:
        raise SearchValidationError("top_k must be between 1 and 50")

    try:
        vectors = embed_texts(
            [q],
            model_id=settings.embedding_model_id,
            project_id=settings.gcp_project_id,
            location=settings.vertex_location,
            batch_size=settings.embedding_batch_size,
            embedder=embedder,
        )
    except EmbeddingError as exc:
        raise SearchServiceError(f"Query embedding failed: {exc.message}") from exc

    if not vectors or not vectors[0]:
        raise SearchServiceError("Query embedding returned empty vector")

    client = query_client or _match_client(settings)
    try:
        hits: list[NeighborHit] = find_neighbors(
            client=client,
            query_embedding=vectors[0],
            top_k=k,
            collection=collection,
        )
    except VectorSearchError as exc:
        raise SearchServiceError(exc.message) from exc

    results = [
        SearchResultItem(
            text=h.text,
            score=h.score,
            document_id=h.document_id,
            version_id=h.version_id,
            chunk_index=h.chunk_index,
            title=h.title,
            filename=h.filename,
            collection=h.collection,
            datapoint_id=h.datapoint_id,
            char_count=h.char_count,
        )
        for h in hits
    ]
    logger.info(
        "dense_search_ok results=%s top_k=%s collection=%s",
        len(results),
        k,
        collection or "",
    )
    return SearchResponse(query=q, top_k=k, results=results)
