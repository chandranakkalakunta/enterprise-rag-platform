# Dense-only baseline (Phase 4.1)

**Date:** 2026-07-19  
**Mode:** `fixture` (CI-reproducible) + instructions for live  
**Golden set:** `eval/golden/golden_set.jsonl` (**25** cases)  
**top_k:** 5  

## Fixture baseline (harness correctness)

Command:

```bash
python -m eval.harness --mode fixture --out eval/results/baseline-dense-fixture.json
```

| Aggregate | Value |
|-----------|-------|
| total | 25 |
| errors | 0 |
| refusal_accuracy | 1.0 (n=25 cases scored) |
| recall_rate | 1.0 (n=21; 4 pure-refusal N/A) |
| mean_list_completeness | 1.0 (n=21 with must_include) |

**Interpretation:** Fixture responses embed expected tokens by construction. This proves the **metrics pipeline** works; it is **not** a measure of production RAG quality.

Artifact: `eval/results/baseline-dense-fixture.json` (regenerate via CLI).

## Live dense baseline (Coordinator)

1. Ensure published corpus covers product docs themes (or upload golden-aligned PDFs/MD).  
2. Run live harness per [rag-eval-harness.md](../runbooks/rag-eval-harness.md).  
3. Paste summary rates below and commit `eval/results/baseline-dense-live.json` when available.

| Aggregate | Live value (fill when run) |
|-----------|----------------------------|
| total | |
| errors | |
| refusal_accuracy | |
| recall_rate | |
| mean_list_completeness | |

### Qualitative groundedness notes (live)

- Review sample answers for inventing facts outside citations.  
- List questions (e.g. Phase 5.0–5.4) often under-complete under dense-only + top_k=5 — primary hybrid motivator (ADR-0011).  
- Lexical cases (`datapoint.json`, secret IDs) may fail dense Recall@k proxy until BM25 (4.2).

## Case mix

| Category | Count (approx) | Examples |
|----------|----------------|----------|
| factoid / definition | 5 | region, allowlist, top_k, Firestore |
| list / table | 6 | roles, Cloud Run services, Phase 5 slices, ADR-0011 metrics |
| refusal | 4 | PII, missing phase, market data, HR |
| doc_specific | 8 | version reload, embeddings model, PWA native-out |
| lexical | 2 | Vector Search bootstrap filename, OAuth secret ids |

## Gate / comparison for hybrid (Phase 4.2)

Hybrid is implemented with `HYBRID_RETRIEVAL_ENABLED` (default true in code; set false for dense-only rollback).  
Re-run live eval after hybrid deploy:

```bash
python -m eval.harness --mode live --path answer --out eval/results/baseline-hybrid-live.json
```

Expect improvement on **recall_rate** and **mean_list_completeness** vs dense baseline (~0.48 / ~0.04 live reported) with limited refusal degradation.
