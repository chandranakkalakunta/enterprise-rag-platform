"""RAG evaluation harness (Phase 4.1 / ADR-0011).

Dense-only baseline tooling. Hybrid evaluation lands in Phase 4.2+.
"""

from eval.harness.metrics import (
    list_completeness,
    recall_at_k_proxy,
    refusal_correctness,
    score_case,
)
from eval.harness.load import load_golden_set

__all__ = [
    "load_golden_set",
    "list_completeness",
    "recall_at_k_proxy",
    "refusal_correctness",
    "score_case",
]
