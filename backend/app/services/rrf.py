"""Reciprocal Rank Fusion (Phase 4.2 / ADR-0011).

Pure functions — no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RankedItem(Generic[T]):
    """One ranked retrieval hit with a fusion key."""

    key: str
    item: T
    rank: int  # 1-based rank in its channel
    score: float = 0.0  # original channel score (informational)


def rrf_score(rank: int, k: int = 60) -> float:
    """Single-list RRF contribution for 1-based rank."""
    if rank < 1:
        raise ValueError("rank must be 1-based (>= 1)")
    if k < 1:
        raise ValueError("k must be >= 1")
    return 1.0 / (k + rank)


def fuse_rrf(
    ranked_lists: Sequence[Sequence[RankedItem[T]]],
    *,
    k: int = 60,
    top_k: int = 5,
) -> list[tuple[str, T, float]]:
    """Fuse multiple ranked lists with Reciprocal Rank Fusion.

    Returns list of (key, item, rrf_score) sorted by score desc, length <= top_k.
    When the same key appears in multiple lists, scores sum; first-seen item wins.
    """
    if top_k < 1:
        return []
    if k < 1:
        raise ValueError("k must be >= 1")

    scores: dict[str, float] = {}
    items: dict[str, T] = {}

    for ranked in ranked_lists:
        for entry in ranked:
            if not entry.key:
                continue
            contrib = rrf_score(entry.rank, k=k)
            scores[entry.key] = scores.get(entry.key, 0.0) + contrib
            if entry.key not in items:
                items[entry.key] = entry.item

    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    out: list[tuple[str, T, float]] = []
    for key, score in ordered[:top_k]:
        out.append((key, items[key], score))
    return out
