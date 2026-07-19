"""Pure scoring functions (ADR-0011 Phase 4.1 metrics)."""

from __future__ import annotations

from eval.harness.models import CaseScore, GoldenCase, ModelResponse, RetrievalHit


def _norm(s: str) -> str:
    return (s or "").casefold()


def _contains(haystack: str, needle: str) -> bool:
    return _norm(needle) in _norm(haystack)


def corpus_blob(hits: list[RetrievalHit], answer: str = "") -> str:
    """Concatenate retrieval texts, filenames, titles, and optional answer."""
    parts: list[str] = [answer or ""]
    for h in hits:
        parts.append(h.text or "")
        if h.filename:
            parts.append(h.filename)
        if h.title:
            parts.append(h.title)
        if h.document_id:
            parts.append(h.document_id)
    return "\n".join(parts)


def recall_at_k_proxy(
    case: GoldenCase,
    hits: list[RetrievalHit],
    *,
    answer: str = "",
) -> tuple[bool | None, list[str], list[str]]:
    """Proxy Recall@k: expected strings appear in top-k hit text/filename/title.

    Uses ``must_include`` and ``relevant_doc_hints`` as expected evidence tokens.
    Returns (ok, hits_found, misses). None if no expected tokens (N/A).
    """
    expected = list(case.must_include) + list(case.relevant_doc_hints)
    # For refusal cases with no expected evidence, recall is N/A
    if case.should_refuse and not expected:
        return None, [], []
    if not expected:
        return None, [], []

    blob = corpus_blob(hits, answer="")
    # Also allow answer text as weak signal only if hits empty (answer-only mode)
    if not hits and answer:
        blob = corpus_blob([], answer=answer)

    found: list[str] = []
    misses: list[str] = []
    for token in expected:
        if _contains(blob, token):
            found.append(token)
        else:
            misses.append(token)

    # Recall proxy success: at least one expected token present (Recall@k-style hit)
    # For list cases we still report partial via list_completeness separately.
    ok = len(found) > 0
    return ok, found, misses


def list_completeness(case: GoldenCase, answer: str) -> tuple[float | None, list[str], list[str]]:
    """Fraction of must_include strings found in the answer text.

    N/A when must_include is empty or case is a pure refusal with no items.
    """
    items = list(case.must_include)
    if not items:
        return None, [], []
    if case.should_refuse:
        # Refusal cases usually have empty must_include; if present, still score
        pass

    found: list[str] = []
    misses: list[str] = []
    for token in items:
        if _contains(answer, token):
            found.append(token)
        else:
            misses.append(token)
    return len(found) / len(items), found, misses


def refusal_correctness(should_refuse: bool, refused: bool) -> bool:
    return should_refuse == refused


def score_case(case: GoldenCase, response: ModelResponse | None, *, error: str | None = None) -> CaseScore:
    """Score one case against a model/fixture response."""
    if error or response is None:
        return CaseScore(
            case_id=case.id,
            category=case.category,
            should_refuse=case.should_refuse,
            refused=False,
            refusal_ok=None,
            recall_ok=None,
            list_completeness=None,
            must_include_hits=[],
            must_include_misses=list(case.must_include),
            notes=case.notes,
            error=error or "missing response",
        )

    refuse_ok = refusal_correctness(case.should_refuse, response.refused)
    # Retrieval proxy: prefer hits; if answer mode and no hits, use answer blob weakly for hints
    recall_ok, _rf, _rm = recall_at_k_proxy(case, response.hits, answer=response.answer)
    # List completeness always from answer (generation quality)
    list_comp, list_hits, list_misses = list_completeness(case, response.answer)

    return CaseScore(
        case_id=case.id,
        category=case.category,
        should_refuse=case.should_refuse,
        refused=response.refused,
        refusal_ok=refuse_ok,
        recall_ok=recall_ok,
        list_completeness=list_comp,
        must_include_hits=list_hits,
        must_include_misses=list_misses,
        notes=case.notes,
        error=None,
    )


def aggregate(cases: list[CaseScore], *, mode: str, top_k: int) -> dict:
    """Build SuiteSummary-compatible dict with aggregate rates."""
    errors = sum(1 for c in cases if c.error)
    refuse_scored = [c for c in cases if c.refusal_ok is not None and not c.error]
    recall_scored = [c for c in cases if c.recall_ok is not None and not c.error]
    list_scored = [c for c in cases if c.list_completeness is not None and not c.error]

    def _mean_bool(vals: list[bool]) -> float | None:
        if not vals:
            return None
        return sum(1 for v in vals if v) / len(vals)

    return {
        "total": len(cases),
        "errors": errors,
        "refusal_accuracy": _mean_bool([bool(c.refusal_ok) for c in refuse_scored]),
        "refusal_n": len(refuse_scored),
        "recall_rate": _mean_bool([bool(c.recall_ok) for c in recall_scored]),
        "recall_n": len(recall_scored),
        "mean_list_completeness": (
            sum(float(c.list_completeness or 0) for c in list_scored) / len(list_scored)
            if list_scored
            else None
        ),
        "list_n": len(list_scored),
        "mode": mode,
        "top_k": top_k,
        "cases": [c.to_dict() for c in cases],
    }
