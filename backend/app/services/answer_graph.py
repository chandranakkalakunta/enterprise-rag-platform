"""LangGraph retrieve → evidence_check → generate_or_refuse (Phase 3.4 / ADR-0008).

Simple linear graph. Nodes are pure-ish and injectable via callables for tests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, TypedDict

from langgraph.graph import END, StateGraph

from app.core.config import Settings
from app.services.evidence import EvidenceDecision, check_evidence
from app.services.generation import (
    SAFE_REFUSAL_ANSWER,
    EvidenceSnippet,
    GenerationError,
    TextGenerator,
    generate_grounded_answer,
)
from app.services.hybrid_search import hybrid_search
from app.services.search import (
    SearchResponse,
    SearchResultItem,
    SearchServiceError,
    SearchValidationError,
)
from app.services.embeddings import TextEmbedder
from app.services.vector_search import VectorQueryClient

logger = logging.getLogger("erp.api.answer_graph")


class AnswerGraphState(TypedDict, total=False):
    query: str
    top_k: int | None
    collection: str | None
    hits: list[SearchResultItem]
    retrieval_top_k: int
    evidence_ok: bool
    refusal_reason: str | None
    usable_hit_count: int
    answer: str
    refused: bool
    citations: list[dict[str, Any]]
    error: str | None


@dataclass(frozen=True, slots=True)
class Citation:
    document_id: str | None
    version_id: str | None
    chunk_index: int | None
    title: str | None
    filename: str | None
    snippet: str
    score: float


@dataclass(frozen=True, slots=True)
class AnswerResult:
    query: str
    answer: str
    refused: bool
    refusal_reason: str | None
    citations: list[Citation]
    top_k: int
    hit_count: int


def hits_to_snippets(hits: list[SearchResultItem]) -> list[EvidenceSnippet]:
    snippets: list[EvidenceSnippet] = []
    n = 0
    for h in hits:
        text = (h.text or "").strip()
        if not text or text == " ":
            continue
        n += 1
        snippets.append(
            EvidenceSnippet(
                index=n,
                document_id=h.document_id,
                version_id=h.version_id,
                chunk_index=h.chunk_index,
                title=h.title,
                filename=h.filename,
                text=text,
                score=float(h.score),
            )
        )
    return snippets


def hits_to_citations(hits: list[SearchResultItem]) -> list[Citation]:
    citations: list[Citation] = []
    for h in hits:
        text = (h.text or "").strip()
        if not text or text == " ":
            continue
        snippet = text if len(text) <= 400 else text[:400] + "…"
        citations.append(
            Citation(
                document_id=h.document_id,
                version_id=h.version_id,
                chunk_index=h.chunk_index,
                title=h.title,
                filename=h.filename,
                snippet=snippet,
                score=float(h.score),
            )
        )
    return citations


def build_answer_graph(
    *,
    settings: Settings,
    embedder: TextEmbedder | None = None,
    query_client: VectorQueryClient | None = None,
    generator: TextGenerator | None = None,
    search_fn: Callable[..., SearchResponse] | None = None,
):
    """Compile LangGraph: retrieve → evidence_check → generate_or_refuse."""

    # Phase 4.2: hybrid dense+BM25+RRF when enabled; dense-only when flag off
    search = search_fn or hybrid_search

    def retrieve(state: AnswerGraphState) -> AnswerGraphState:
        result = search(
            settings=settings,
            query=state["query"],
            top_k=state.get("top_k"),
            collection=state.get("collection"),
            embedder=embedder,
            query_client=query_client,
        )
        return {
            **state,
            "hits": list(result.results),
            "retrieval_top_k": result.top_k,
            "error": None,
        }

    def evidence_check(state: AnswerGraphState) -> AnswerGraphState:
        decision: EvidenceDecision = check_evidence(
            state.get("hits") or [],
            min_score=settings.evidence_min_score,
        )
        return {
            **state,
            "evidence_ok": decision.ok,
            "refusal_reason": decision.reason,
            "usable_hit_count": decision.usable_hit_count,
        }

    def generate_or_refuse(state: AnswerGraphState) -> AnswerGraphState:
        if not state.get("evidence_ok"):
            return {
                **state,
                "refused": True,
                "answer": SAFE_REFUSAL_ANSWER,
                "citations": [],
            }
        hits = list(state.get("hits") or [])
        snippets = hits_to_snippets(hits)
        try:
            answer = generate_grounded_answer(
                query=state["query"],
                snippets=snippets,
                model_id=settings.generation_model_id,
                project_id=settings.gcp_project_id,
                location=settings.vertex_location,
                temperature=settings.generation_temperature,
                generator=generator,
            )
        except GenerationError as exc:
            # Surface as graph error for API mapping
            return {
                **state,
                "error": exc.message,
                "refused": False,
                "answer": "",
                "citations": [],
            }
        citations = [
            {
                "document_id": c.document_id,
                "version_id": c.version_id,
                "chunk_index": c.chunk_index,
                "title": c.title,
                "filename": c.filename,
                "snippet": c.snippet,
                "score": c.score,
            }
            for c in hits_to_citations(hits)
        ]
        return {
            **state,
            "refused": False,
            "refusal_reason": None,
            "answer": answer,
            "citations": citations,
        }

    graph = StateGraph(AnswerGraphState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("evidence_check", evidence_check)
    graph.add_node("generate_or_refuse", generate_or_refuse)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "evidence_check")
    graph.add_edge("evidence_check", "generate_or_refuse")
    graph.add_edge("generate_or_refuse", END)
    return graph.compile()


def run_grounded_answer(
    *,
    settings: Settings,
    query: str,
    top_k: int | None = None,
    collection: str | None = None,
    embedder: TextEmbedder | None = None,
    query_client: VectorQueryClient | None = None,
    generator: TextGenerator | None = None,
    search_fn: Callable[..., SearchResponse] | None = None,
) -> AnswerResult:
    """Execute the grounded-answer graph and map to AnswerResult."""
    q = (query or "").strip()
    if not q:
        raise SearchValidationError("query must be a non-empty string")

    app = build_answer_graph(
        settings=settings,
        embedder=embedder,
        query_client=query_client,
        generator=generator,
        search_fn=search_fn,
    )
    initial: AnswerGraphState = {
        "query": q,
        "top_k": top_k,
        "collection": collection,
    }
    try:
        final = app.invoke(initial)
    except SearchValidationError:
        raise
    except SearchServiceError:
        raise
    except Exception as exc:  # noqa: BLE001
        # dense_search raises SearchServiceError; re-raise others as service error
        if isinstance(exc, (SearchValidationError, SearchServiceError)):
            raise
        logger.exception("answer_graph_failed")
        raise SearchServiceError(f"Answer pipeline failed: {exc}") from exc

    if final.get("error"):
        raise SearchServiceError(final["error"])

    citations_raw = final.get("citations") or []
    citations = [
        Citation(
            document_id=c.get("document_id"),
            version_id=c.get("version_id"),
            chunk_index=c.get("chunk_index"),
            title=c.get("title"),
            filename=c.get("filename"),
            snippet=c.get("snippet") or "",
            score=float(c.get("score") or 0.0),
        )
        for c in citations_raw
    ]
    hits = final.get("hits") or []
    return AnswerResult(
        query=q,
        answer=final.get("answer") or "",
        refused=bool(final.get("refused")),
        refusal_reason=final.get("refusal_reason"),
        citations=citations,
        top_k=int(final.get("retrieval_top_k") or top_k or settings.retrieval_top_k),
        hit_count=len(hits),
    )
