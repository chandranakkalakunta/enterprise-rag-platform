"""Unit tests for evidence check (Phase 3.4)."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.evidence import (
    REFUSAL_LOW_SCORE,
    REFUSAL_NO_HITS,
    REFUSAL_NO_USABLE_TEXT,
    check_evidence,
)


@dataclass
class Hit:
    text: str | None
    score: float


def test_zero_hits_refuse() -> None:
    d = check_evidence([])
    assert d.ok is False
    assert d.reason == REFUSAL_NO_HITS


def test_empty_text_refuse() -> None:
    d = check_evidence([Hit(text="  ", score=0.9), Hit(text=None, score=0.8)])
    assert d.ok is False
    assert d.reason == REFUSAL_NO_USABLE_TEXT


def test_usable_hits_pass() -> None:
    d = check_evidence([Hit(text="Policy text", score=0.5)])
    assert d.ok is True
    assert d.reason is None
    assert d.usable_hit_count == 1


def test_min_score_threshold() -> None:
    d = check_evidence(
        [Hit(text="a", score=0.1), Hit(text="b", score=0.2)],
        min_score=0.5,
    )
    assert d.ok is False
    assert d.reason == REFUSAL_LOW_SCORE

    d2 = check_evidence(
        [Hit(text="a", score=0.6)],
        min_score=0.5,
    )
    assert d2.ok is True
