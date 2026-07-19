"""Hybrid dense + BM25 retrieval with RRF (Phase 4.2 / ADR-0011)."""

from __future__ import annotations

import logging
from typing import Callable

from app.core.config import Settings
from app.services.bm25_index import InProcessBM25Index, get_bm25_index
from app.services.embeddings import TextEmbedder
from app.services.rrf import RankedItem, fuse_rrf
from app.services.search import (
    SearchResponse,
    SearchResultItem,
    SearchServiceError,
    SearchValidationError,
    dense_search,
)
from app.services.vector_search import VectorQueryClient

logger = logging.getLogger("erp.api.hybrid")


def _bm25_to_result(chunk, score: float) -> SearchResultItem:
    return SearchResultItem(
        text=chunk.text,
        score=float(score),
        document_id=chunk.document_id,
        version_id=chunk.version_id,
        chunk_index=chunk.chunk_index,
        title=chunk.title,
        filename=chunk.filename,
        collection=chunk.collection,
        datapoint_id=chunk.datapoint_id,
        char_count=len(chunk.text or ""),
    )


def _to_ranked(
    results: list[SearchResultItem],
) -> list[RankedItem[SearchResultItem]]:
    ranked: list[RankedItem[SearchResultItem]] = []
    for i, item in enumerate(results, start=1):
        key = item.datapoint_id or f"{item.document_id}:{item.version_id}:{item.chunk_index}"
        ranked.append(RankedItem(key=key, item=item, rank=i, score=float(item.score)))
    return ranked


def hybrid_search(
    *,
    settings: Settings,
    query: str,
    top_k: int | None = None,
    collection: str | None = None,
    embedder: TextEmbedder | None = None,
    query_client: VectorQueryClient | None = None,
    bm25_index: InProcessBM25Index | None = None,
    dense_fn: Callable[..., SearchResponse] | None = None,
) -> SearchResponse:
    """
    Feature-flagged hybrid retrieval.

    - HYBRID_RETRIEVAL_ENABLED=false → dense_search only
    - hybrid on: dense top_k_dense ∥ BM25 top_k_bm25 → RRF → final top_k
    - If BM25 empty/unavailable: dense-only (no failure)
    - Dense failure still raises (unless we only had BM25 — not default)
    """
    q = (query or "").strip()
    if not q:
        raise SearchValidationError("query must be a non-empty string")

    final_k = top_k if top_k is not None else settings.retrieval_top_k
    if final_k < 1 or final_k > 50:
        raise SearchValidationError("top_k must be between 1 and 50")

    dense = dense_fn or dense_search

    if not settings.hybrid_retrieval_enabled:
        return dense(
            settings=settings,
            query=q,
            top_k=final_k,
            collection=collection,
            embedder=embedder,
            query_client=query_client,
        )

    k_dense = settings.retrieval_top_k_dense or final_k
    k_bm25 = settings.retrieval_top_k_bm25 or final_k
    rrf_k = settings.rrf_k

    # Dense channel (required path when Vector Search is the primary store)
    dense_resp = dense(
        settings=settings,
        query=q,
        top_k=k_dense,
        collection=collection,
        embedder=embedder,
        query_client=query_client,
    )
    dense_ranked = _to_ranked(list(dense_resp.results))

    # BM25 channel (published corpus only; empty index → skip)
    bm25_ranked: list[RankedItem[SearchResultItem]] = []
    idx = bm25_index or get_bm25_index()
    try:
        bm25_hits = idx.search(q, top_k=k_bm25, collection=collection)
        for i, (chunk, score) in enumerate(bm25_hits, start=1):
            item = _bm25_to_result(chunk, score)
            bm25_ranked.append(
                RankedItem(key=item.datapoint_id, item=item, rank=i, score=score)
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("bm25_search_failed falling_back_dense_only err=%s", exc)
        bm25_ranked = []

    if not bm25_ranked:
        # Dense-only fallback when BM25 empty/disabled path
        results = list(dense_resp.results)[:final_k]
        logger.info(
            "hybrid_dense_only results=%s (bm25 empty) top_k=%s",
            len(results),
            final_k,
        )
        return SearchResponse(query=q, top_k=final_k, results=results)

    fused = fuse_rrf(
        [dense_ranked, bm25_ranked],
        k=rrf_k,
        top_k=final_k,
    )
    results = [
        SearchResultItem(
            text=item.text,
            score=rrf_score,  # RRF score for ranking transparency
            document_id=item.document_id,
            version_id=item.version_id,
            chunk_index=item.chunk_index,
            title=item.title,
            filename=item.filename,
            collection=item.collection,
            datapoint_id=item.datapoint_id,
            char_count=item.char_count,
        )
        for _key, item, rrf_score in fused
    ]
    logger.info(
        "hybrid_search_ok dense=%s bm25=%s fused=%s top_k=%s rrf_k=%s",
        len(dense_ranked),
        len(bm25_ranked),
        len(results),
        final_k,
        rrf_k,
    )
    return SearchResponse(query=q, top_k=final_k, results=results)
