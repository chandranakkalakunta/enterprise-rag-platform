# Phase 4 Engineering Report — RAG Quality MVP

**Date:** 2026-07-19  
**Status:** Complete  

## Scope

Improve retrieval/answer quality with **measurement first**, then hybrid lexical + dense fusion, without changing the product API surface.

## Outcomes

| Area | Delivered |
|------|-----------|
| Decision | ADR-0011 (eval + hybrid BM25/dense/RRF) |
| Eval | `eval/golden/golden_set.jsonl`, `python -m eval.harness`, fixture baseline |
| Retrieve | `hybrid_search` → LangGraph + `/query/search` & `/query/answer` |
| BM25 | In-process Okapi; publish/retire hooks; startup warm-start |
| Citations | `CITATION_MAX_PER_DOC` (default 1); FE safety-net dedupe |
| Rollback | `HYBRID_RETRIEVAL_ENABLED=false` → dense-only |

## Key config (ops)

| Variable | Role |
|----------|------|
| `HYBRID_RETRIEVAL_ENABLED` | Hybrid on/off |
| `RRF_K` | RRF constant (default 60) |
| `RETRIEVAL_TOP_K` / `_DENSE` / `_BM25` | Channel depths |
| `BM25_WARM_START` / `_MAX_DOCS` | Startup index rebuild |
| `CITATION_MAX_PER_DOC` / `CITATION_MERGE_SNIPPETS` | SOURCES UX |
| `GENERATION_MODEL_ID` | Pin current Gemini (e.g. `gemini-2.5-flash`) |

## Test posture

- Unit/API tests for RRF, BM25, hybrid flag, citation dedupe, warm-start (mocked GCS/Firestore).  
- CI does not require live Vertex.  
- Live eval remains operator-driven.

## Artifacts

- ADR: [0011](../adr/0011-rag-evaluation-and-hybrid-retrieval.md)  
- Runbooks: [rag-eval-harness](../runbooks/rag-eval-harness.md), [citation-dedupe-bm25-warm](../runbooks/citation-dedupe-bm25-warm.md)  
- Retro: [phase-4.md](../retrospectives/phase-4.md)  

## Recommendation

Close Phase 4 as **quality MVP complete**. Next operational priority: **Cloud Run zero-touch UI cutover** (auth secrets, CORS/OAuth origins, public frontend env, hybrid flags). Deeper RAG features (multi-turn, OpenSearch, streaming, cache) stay backlog.  
