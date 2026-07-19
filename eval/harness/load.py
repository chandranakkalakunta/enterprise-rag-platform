"""Load golden set JSONL and fixture response maps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from eval.harness.models import GoldenCase, ModelResponse, RetrievalHit


def load_golden_set(path: str | Path) -> list[GoldenCase]:
    """Load versioned golden set (one JSON object per line)."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Golden set not found: {p}")
    cases: list[GoldenCase] = []
    with p.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{p}:{line_no}: invalid JSON: {exc}") from exc
            cases.append(GoldenCase.from_dict(raw))
    if not cases:
        raise ValueError(f"Golden set is empty: {p}")
    return cases


def _hit_from_dict(raw: dict[str, Any]) -> RetrievalHit:
    return RetrievalHit(
        text=str(raw.get("text") or raw.get("snippet") or ""),
        filename=raw.get("filename"),
        title=raw.get("title"),
        document_id=raw.get("document_id"),
        score=float(raw.get("score") or 0.0),
    )


def model_response_from_dict(raw: dict[str, Any], *, source: str = "fixture") -> ModelResponse:
    hits_raw = raw.get("hits") or raw.get("results") or []
    citations = raw.get("citations") or []
    hits: list[RetrievalHit] = []
    for h in hits_raw:
        if isinstance(h, dict):
            hits.append(_hit_from_dict(h))
    for c in citations:
        if isinstance(c, dict):
            hits.append(
                RetrievalHit(
                    text=str(c.get("snippet") or ""),
                    filename=c.get("filename"),
                    title=c.get("title"),
                    document_id=c.get("document_id"),
                    score=float(c.get("score") or 0.0),
                )
            )
    return ModelResponse(
        answer=str(raw.get("answer") or ""),
        refused=bool(raw.get("refused", False)),
        refusal_reason=raw.get("refusal_reason"),
        hits=hits,
        source=source,
    )


def load_fixture_map(path: str | Path) -> dict[str, ModelResponse]:
    """Load case_id → response mapping from JSON object or list."""
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    out: dict[str, ModelResponse] = {}
    if isinstance(data, dict) and "responses" in data:
        data = data["responses"]
    if isinstance(data, dict):
        for case_id, payload in data.items():
            out[str(case_id)] = model_response_from_dict(payload, source="fixture")
    elif isinstance(data, list):
        for item in data:
            case_id = str(item["id"])
            out[case_id] = model_response_from_dict(item, source="fixture")
    else:
        raise ValueError(f"Unsupported fixture format: {p}")
    return out


def write_json(path: str | Path, payload: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def format_table(cases: Iterable[dict[str, Any]]) -> str:
    """Simple fixed-width summary table for humans."""
    rows = list(cases)
    if not rows:
        return "(no cases)"
    headers = ["id", "cat", "refuse_ok", "recall", "list_comp", "error"]
    lines = [" | ".join(headers), "-|-".join("-" * len(h) for h in headers)]
    for r in rows:
        lines.append(
            " | ".join(
                [
                    str(r.get("case_id", ""))[:12],
                    str(r.get("category", ""))[:10],
                    _fmt_bool(r.get("refusal_ok")),
                    _fmt_bool(r.get("recall_ok")),
                    _fmt_float(r.get("list_completeness")),
                    str(r.get("error") or "")[:24],
                ]
            )
        )
    return "\n".join(lines)


def _fmt_bool(v: Any) -> str:
    if v is None:
        return "-"
    return "Y" if v else "N"


def _fmt_float(v: Any) -> str:
    if v is None:
        return "-"
    return f"{float(v):.2f}"
