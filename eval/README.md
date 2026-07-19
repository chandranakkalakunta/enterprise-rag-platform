# Evaluation (Phase 4.1+)

Held-out golden set and dense-only baseline harness per [ADR-0011](../docs/adr/0011-rag-evaluation-and-hybrid-retrieval.md).

## Quick start

```bash
# From repository root
python -m eval.harness --mode fixture --out eval/results/baseline-dense-fixture.json
```

Live API:

```bash
export EVAL_API_BASE=http://localhost:8000
export EVAL_BEARER_TOKEN=...   # if AUTH_DEV_BYPASS=false
python -m eval.harness --mode live --path answer --out eval/results/baseline-dense-live.json
```

See [docs/runbooks/rag-eval-harness.md](../docs/runbooks/rag-eval-harness.md).
