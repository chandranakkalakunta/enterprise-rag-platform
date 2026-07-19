"""Dataclasses for golden cases and harness I/O."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class GoldenCase:
    """One held-out evaluation case (versioned in golden_set.jsonl)."""

    id: str
    question: str
    should_refuse: bool
    relevant_doc_hints: list[str] = field(default_factory=list)
    must_include: list[str] = field(default_factory=list)
    notes: str = ""
    category: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> GoldenCase:
        if not raw.get("id") or not raw.get("question"):
            raise ValueError(f"Golden case missing id/question: {raw!r}")
        return cls(
            id=str(raw["id"]),
            question=str(raw["question"]),
            should_refuse=bool(raw.get("should_refuse", False)),
            relevant_doc_hints=[str(x) for x in (raw.get("relevant_doc_hints") or [])],
            must_include=[str(x) for x in (raw.get("must_include") or [])],
            notes=str(raw.get("notes") or ""),
            category=str(raw.get("category") or ""),
        )


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    """Minimal retrieval hit for scoring (search or citation-derived)."""

    text: str = ""
    filename: str | None = None
    title: str | None = None
    document_id: str | None = None
    score: float = 0.0


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Answer (+ optional retrieval hits) from live API or fixture."""

    answer: str
    refused: bool
    refusal_reason: str | None = None
    hits: list[RetrievalHit] = field(default_factory=list)
    source: str = "unknown"  # fixture | live_answer | live_search


@dataclass(frozen=True, slots=True)
class CaseScore:
    case_id: str
    category: str
    should_refuse: bool
    refused: bool
    refusal_ok: bool | None
    recall_ok: bool | None
    list_completeness: float | None
    must_include_hits: list[str]
    must_include_misses: list[str]
    notes: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SuiteSummary:
    total: int
    errors: int
    refusal_accuracy: float | None
    refusal_n: int
    recall_rate: float | None
    recall_n: int
    mean_list_completeness: float | None
    list_n: int
    mode: str
    top_k: int
    cases: list[CaseScore]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "errors": self.errors,
            "refusal_accuracy": self.refusal_accuracy,
            "refusal_n": self.refusal_n,
            "recall_rate": self.recall_rate,
            "recall_n": self.recall_n,
            "mean_list_completeness": self.mean_list_completeness,
            "list_n": self.list_n,
            "mode": self.mode,
            "top_k": self.top_k,
            "cases": [c.to_dict() for c in self.cases],
        }
