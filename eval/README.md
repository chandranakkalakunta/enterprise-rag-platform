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

## Comparing hybrid vs dense (Phase 4.2+)

After deploying hybrid (`HYBRID_RETRIEVAL_ENABLED=true`) with a BM25-warmed corpus
(publish documents so the in-process index is populated on each instance):

```bash
# Dense-only baseline (flag off)
export HYBRID_RETRIEVAL_ENABLED=false   # on the API service
python -m eval.harness --mode live --path answer \
  --out eval/results/baseline-dense-live.json

# Hybrid
export HYBRID_RETRIEVAL_ENABLED=true
python -m eval.harness --mode live --path answer \
  --out eval/results/baseline-hybrid-live.json
```

Compare `recall_rate`, `mean_list_completeness`, and `refusal_accuracy` between the two JSON reports (and vs fixture baseline in `eval/results/baseline-dense-fixture.json`).
