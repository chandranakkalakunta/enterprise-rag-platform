"""Citation packaging helpers (Phase 4.3 — document-level dedupe)."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol, Sequence, TypeVar


class CitationLike(Protocol):
    document_id: str | None
    score: float
    snippet: str


T = TypeVar("T", bound=CitationLike)


def _doc_key(c: CitationLike) -> str:
    did = (c.document_id or "").strip()
    return did if did else f"__nodoc__:{id(c)}"


def _snippet_distinct(a: str, b: str) -> bool:
    sa = (a or "").strip()
    sb = (b or "").strip()
    if not sb:
        return False
    if not sa:
        return True
    # Consider distinct if neither is a prefix of the other (case-insensitive)
    la, lb = sa.casefold(), sb.casefold()
    if la == lb:
        return False
    if la in lb or lb in la:
        return False
    return True


def dedupe_citations_by_document(
    citations: Sequence[T],
    *,
    max_per_doc: int = 1,
    merge_snippets: bool = True,
    max_merged_chars: int = 500,
) -> list[T]:
    """Dedupe citations by document_id, keeping highest scores first.

    Default max_per_doc=1: one card per document.
    When merge_snippets=True and max_per_doc=1, append up to one extra distinct
    snippet from the same doc onto the winner (separated by `` | ``).

    Order of first-seen document groups follows first appearance in input
    (which is typically rank order from retrieval).
    """
    if max_per_doc < 1:
        return []
    if not citations:
        return []

    # Group preserving rank order of first occurrence
    groups: dict[str, list[T]] = {}
    order: list[str] = []
    for c in citations:
        key = _doc_key(c)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(c)

    out: list[T] = []
    for key in order:
        group = sorted(groups[key], key=lambda x: float(x.score), reverse=True)
        kept = group[:max_per_doc]
        if (
            merge_snippets
            and max_per_doc == 1
            and len(group) > 1
            and hasattr(kept[0], "snippet")
        ):
            winner = kept[0]
            for other in group[1:]:
                if _snippet_distinct(winner.snippet, other.snippet):
                    merged = (winner.snippet or "").rstrip()
                    extra = (other.snippet or "").strip()
                    if len(extra) > 200:
                        extra = extra[:200] + "…"
                    combined = f"{merged} | {extra}"
                    if len(combined) > max_merged_chars:
                        combined = combined[: max_merged_chars - 1] + "…"
                    # dataclasses (Citation) support replace; plain objects skip merge
                    try:
                        winner = replace(winner, snippet=combined)  # type: ignore[arg-type]
                    except TypeError:
                        pass
                    kept = [winner]
                    break
        out.extend(kept)
    return out
