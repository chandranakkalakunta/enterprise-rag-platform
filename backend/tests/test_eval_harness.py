"""Phase 4.1 — eval harness unit tests (no Vertex / no live API)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval.harness.client import FixtureClient
from eval.harness.load import load_fixture_map, load_golden_set
from eval.harness.metrics import (
    list_completeness,
    recall_at_k_proxy,
    refusal_correctness,
    score_case,
)
from eval.harness.models import GoldenCase, ModelResponse, RetrievalHit
from eval.harness.run import run_suite

GOLDEN = REPO_ROOT / "eval" / "golden" / "golden_set.jsonl"
FIXTURES = REPO_ROOT / "eval" / "fixtures" / "dense_fixture_responses.json"


def test_golden_set_loads_and_size() -> None:
    cases = load_golden_set(GOLDEN)
    assert len(cases) >= 15
    assert len(cases) <= 40
    ids = {c.id for c in cases}
    assert len(ids) == len(cases)
    # Category coverage
    cats = {c.category for c in cases}
    assert any("refuse" in c or c == "refusal" for c in cats) or any(
        c.should_refuse for c in cases
    )
    assert any(c.must_include for c in cases)


def test_refusal_correctness() -> None:
    assert refusal_correctness(True, True)
    assert refusal_correctness(False, False)
    assert not refusal_correctness(True, False)
    assert not refusal_correctness(False, True)


def test_list_completeness() -> None:
    case = GoldenCase(
        id="t",
        question="q",
        should_refuse=False,
        must_include=["alpha", "beta", "gamma"],
    )
    score, found, misses = list_completeness(
        case, "The items are Alpha and BETA only."
    )
    assert score == pytest.approx(2 / 3)
    assert set(found) == {"alpha", "beta"}
    assert misses == ["gamma"]


def test_recall_at_k_proxy_from_hits() -> None:
    case = GoldenCase(
        id="t",
        question="q",
        should_refuse=False,
        relevant_doc_hints=["ADR-0011"],
        must_include=["RRF"],
    )
    hits = [
        RetrievalHit(
            text="Hybrid uses RRF fusion",
            filename="adr-0011.md",
            title="ADR-0011",
        )
    ]
    ok, found, misses = recall_at_k_proxy(case, hits)
    assert ok is True
    assert "RRF" in found
    assert "ADR-0011" in found
    assert misses == []


def test_recall_na_for_refusal_without_expected() -> None:
    case = GoldenCase(id="r", question="q", should_refuse=True)
    ok, _, _ = recall_at_k_proxy(case, [])
    assert ok is None


def test_score_case_refusal() -> None:
    case = GoldenCase(id="r", question="secret?", should_refuse=True)
    resp = ModelResponse(answer="cannot say", refused=True)
    s = score_case(case, resp)
    assert s.refusal_ok is True
    assert s.recall_ok is None


def test_fixture_suite_runs() -> None:
    cases = load_golden_set(GOLDEN)
    mapping = load_fixture_map(FIXTURES)
    assert set(mapping.keys()) == {c.id for c in cases}
    report = run_suite(cases, FixtureClient(mapping), top_k=5, mode="fixture")
    assert report["errors"] == 0
    assert report["total"] == len(cases)
    assert report["refusal_accuracy"] == 1.0
    assert report["recall_rate"] == 1.0
    assert report["mean_list_completeness"] == 1.0


def test_cli_fixture_entrypoint(tmp_path: Path) -> None:
    from eval.harness.cli import main

    out = tmp_path / "out.json"
    rc = main(
        [
            "--mode",
            "fixture",
            "--golden",
            str(GOLDEN),
            "--fixtures",
            str(FIXTURES),
            "--out",
            str(out),
            "--top-k",
            "5",
        ]
    )
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["total"] >= 15
    assert data["errors"] == 0
