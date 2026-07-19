"""Run evaluation suite over golden cases."""

from __future__ import annotations

from eval.harness.client import AnswerClient
from eval.harness.metrics import aggregate, score_case
from eval.harness.models import CaseScore, GoldenCase


def run_suite(
    cases: list[GoldenCase],
    client: AnswerClient,
    *,
    top_k: int = 5,
    mode: str = "fixture",
) -> dict:
    """Score all cases; return aggregate report dict."""
    scores: list[CaseScore] = []
    for case in cases:
        try:
            response = client.fetch(case, top_k=top_k)
            scores.append(score_case(case, response))
        except Exception as exc:  # noqa: BLE001 — per-case isolation
            scores.append(score_case(case, None, error=str(exc)))
    return aggregate(scores, mode=mode, top_k=top_k)
