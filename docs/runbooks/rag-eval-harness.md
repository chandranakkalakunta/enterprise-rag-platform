# Runbook: RAG evaluation harness (Phase 4.1 / ADR-0011)

**Status:** Dense-only baseline tooling  
**Hybrid:** Phase 4.2 (not enabled here)

## Layout

| Path | Purpose |
|------|---------|
| `eval/golden/golden_set.jsonl` | Held-out golden cases (versioned; no secrets) |
| `eval/harness/` | Pure metrics + CLI |
| `eval/fixtures/dense_fixture_responses.json` | CI/offline canned responses |
| `eval/results/` | Written JSON reports |
| `docs/eval/baseline-dense.md` | Human-readable baseline notes |

## Metrics

| Metric | Definition (Phase 4.1) |
|--------|------------------------|
| **Refusal correctness** | `refused == should_refuse` |
| **Recall@k proxy** | At least one of `must_include` ∪ `relevant_doc_hints` appears in retrieval hit text/filename/title |
| **List completeness** | Fraction of `must_include` found in **answer** text (case-insensitive) |

Groundedness is **not** fully automated yet; note qualitative review in baseline docs. Full LLM-as-judge can land later.

`top_k` defaults to **5** (product `RETRIEVAL_TOP_K`).

## Run — fixture mode (CI / no Vertex)

From **repo root** (so `eval` package imports resolve):

```bash
cd /path/to/enterprise-rag-platform
python -m eval.harness \
  --mode fixture \
  --golden eval/golden/golden_set.jsonl \
  --fixtures eval/fixtures/dense_fixture_responses.json \
  --top-k 5 \
  --out eval/results/baseline-dense-fixture.json
```

Unit tests (from backend venv):

```bash
cd backend
source .venv/bin/activate   # if needed
pytest -q tests/test_eval_harness.py
```

## Run — live API (Coordinator / local with auth)

API must be reachable; auth required unless `AUTH_DEV_BYPASS=true` (dev only).

```bash
export EVAL_API_BASE=https://YOUR-rag-api.run.app   # or http://localhost:8000
export EVAL_BEARER_TOKEN='<Google ID token or bypass-compatible token>'

python -m eval.harness \
  --mode live \
  --path answer \
  --api-base "$EVAL_API_BASE" \
  --token "$EVAL_BEARER_TOKEN" \
  --top-k 5 \
  --out eval/results/baseline-dense-live.json
```

Search-only (no generation):

```bash
python -m eval.harness --mode live --path search --api-base "$EVAL_API_BASE" --token "$EVAL_BEARER_TOKEN"
```

Live results depend on the **published corpus**. Golden cases assume product/docs themes; populate the KB with matching published documents for meaningful live scores.

## Interpreting results

- Fixture suite is expected to score ~1.0 on all rates (perfect canned evidence) — validates the harness, not production quality.  
- Live dense baseline is the **real** Phase 4.1 artifact before hybrid (4.2).  
- Compare hybrid later against the same golden set and `--top-k`.

## Related

- [ADR-0011](../adr/0011-rag-evaluation-and-hybrid-retrieval.md)  
- [baseline-dense.md](../eval/baseline-dense.md)  
