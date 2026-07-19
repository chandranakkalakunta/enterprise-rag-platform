"""CLI: python -m eval.harness ..."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from eval.harness.client import FixtureClient, LiveApiClient
from eval.harness.load import format_table, load_fixture_map, load_golden_set, write_json
from eval.harness.run import run_suite

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLDEN = REPO_ROOT / "eval" / "golden" / "golden_set.jsonl"
DEFAULT_FIXTURES = REPO_ROOT / "eval" / "fixtures" / "dense_fixture_responses.json"
DEFAULT_OUT = REPO_ROOT / "eval" / "results" / "baseline-dense-latest.json"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Phase 4.1 RAG eval harness (dense-only baseline). "
            "Metrics: refusal correctness, Recall@k proxy, list completeness."
        )
    )
    p.add_argument(
        "--golden",
        type=Path,
        default=DEFAULT_GOLDEN,
        help=f"Path to golden_set.jsonl (default: {DEFAULT_GOLDEN})",
    )
    p.add_argument(
        "--mode",
        choices=("fixture", "live"),
        default="fixture",
        help="fixture=canned responses; live=call running API",
    )
    p.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES,
        help="Fixture JSON for --mode fixture",
    )
    p.add_argument(
        "--api-base",
        default=None,
        help="API base URL for live mode (or EVAL_API_BASE env)",
    )
    p.add_argument(
        "--token",
        default=None,
        help="Bearer token for live mode (or EVAL_BEARER_TOKEN)",
    )
    p.add_argument(
        "--path",
        choices=("answer", "search"),
        default="answer",
        help="Live endpoint: full answer or search-only",
    )
    p.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Retrieval top_k (align with RETRIEVAL_TOP_K product default)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Write JSON summary to this path",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of golden cases",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cases = load_golden_set(args.golden)
    if args.limit is not None:
        cases = cases[: max(0, args.limit)]

    if args.mode == "fixture":
        mapping = load_fixture_map(args.fixtures)
        client = FixtureClient(mapping)
        mode = "fixture"
    else:
        import os

        base = args.api_base or os.getenv("EVAL_API_BASE") or "http://localhost:8000"
        client = LiveApiClient(base, token=args.token, path=args.path)
        mode = f"live_{args.path}"

    report = run_suite(cases, client, top_k=args.top_k, mode=mode)
    write_json(args.out, report)

    print("=== RAG eval summary (Phase 4.1 dense baseline) ===")
    print(f"mode={report['mode']}  total={report['total']}  errors={report['errors']}  top_k={report['top_k']}")
    print(
        f"refusal_accuracy={report['refusal_accuracy']!s} (n={report['refusal_n']})  "
        f"recall_rate={report['recall_rate']!s} (n={report['recall_n']})  "
        f"mean_list_completeness={report['mean_list_completeness']!s} (n={report['list_n']})"
    )
    print()
    print(format_table(report["cases"]))
    print()
    print(f"Wrote {args.out}")
    return 0 if report["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
