"""Minimal evidence check for grounded generation (Phase 3.4 / ADR-0008).

Pure functions — no FastAPI / Vertex / LangGraph dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


class EvidenceHit(Protocol):
    """Minimal hit shape for evidence evaluation."""

    text: str | None
    score: float


@dataclass(frozen=True, slots=True)
class EvidenceDecision:
    """Result of evidence_check."""

    ok: bool
    reason: str | None  # set when not ok
    usable_hit_count: int


REFUSAL_NO_HITS = "No published evidence was retrieved for this query."
REFUSAL_NO_USABLE_TEXT = "Retrieved hits had no usable text content."
REFUSAL_LOW_SCORE = "Retrieved evidence scores were below the configured minimum."


def _usable_text(text: str | None) -> bool:
    return bool(text and str(text).strip() and str(text).strip() != " ")


def check_evidence(
    hits: Sequence[EvidenceHit],
    *,
    min_score: float | None = None,
) -> EvidenceDecision:
    """
    MVP evidence gate.

    - Zero hits → refuse
    - Hits without usable text → refuse
    - If min_score is set and every usable hit is below min_score → refuse
    """
    if not hits:
        return EvidenceDecision(ok=False, reason=REFUSAL_NO_HITS, usable_hit_count=0)

    usable = [h for h in hits if _usable_text(h.text)]
    if not usable:
        return EvidenceDecision(
            ok=False, reason=REFUSAL_NO_USABLE_TEXT, usable_hit_count=0
        )

    if min_score is not None:
        above = [h for h in usable if float(h.score) >= float(min_score)]
        if not above:
            return EvidenceDecision(
                ok=False,
                reason=REFUSAL_LOW_SCORE,
                usable_hit_count=len(usable),
            )
        return EvidenceDecision(
            ok=True, reason=None, usable_hit_count=len(above)
        )

    return EvidenceDecision(ok=True, reason=None, usable_hit_count=len(usable))
