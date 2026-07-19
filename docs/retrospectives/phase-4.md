# Phase 4 Retrospective — RAG Quality MVP

**Date:** 2026-07-19  
**Status:** Complete  
**PR range:** #29 – #32 (approx.; ADR-0011 through citation dedupe / BM25 warm-start)

## Summary

Phase 4 delivered a **measurable quality track** on top of Phase 3 dense retrieval: eval harness, hybrid BM25 + dense + RRF, citation dedupe, and BM25 warm-start. Multi-turn, managed search, streaming, and deep refusal tuning stay deferred.

## Delivered

| Sub-phase | What |
|-----------|------|
| **4.0** | ADR-0011 — eval-first; hybrid design (BM25 + dense + RRF); LangGraph `retrieve` extension |
| **4.1** | Golden set (25) + harness (`python -m eval.harness`); dense baseline path |
| **4.2** | In-process Okapi BM25; RRF fusion; hybrid search/answer; publish/retire index hooks |
| **4.3** | Citation dedupe by `document_id`; BM25 warm-start on API startup |

## Lessons

1. **Eval golden set must match the published corpus** — otherwise Recall@k / list completeness stay noisy and mislead “improvement” claims.  
2. **In-process BM25 needs warm-start** — cold Cloud Run instances are dense-only until rebuild or a publish hits that instance.  
3. **Model pins rot** — `gemini-2.0-flash-001` was discontinued; always pin a current `GENERATION_MODEL_ID` and re-check after Google deprecations.  
4. **Hybrid helps lexical misses; citations spam is a separate UX fix** — RRF alone does not stop five SOURCES from one document.  
5. **Eval-first (ADR-0011) paid off** — fixture harness unlocked CI; live comparison remains a Coordinator ops step.

## Deferred (backlog — not incomplete Phase 4 MVP)

| ID / theme | Item |
|------------|------|
| BL-RAG-06 | Multi-turn conversation memory |
| BL-RAG-21 | Managed OpenSearch (or equivalent) for BM25 |
| BL-RAG-08 | Token streaming to client |
| BL-RAG-11 / BL-DEC-06 | Semantic cache |
| BL-RAG-05 | Deep ACL-aware retrieval |
| BL-GRD-* | Fuller guardrails / stronger refusal tuning |
| — | MMR / rerank / advanced top_k policy |

## Residual risks

- Multi-instance BM25 consistency (per-process memory).  
- Warm-start race: first queries after cold start may miss lexical channel.  
- Live golden-set scores still depend on corpus alignment.  
- Refusal correctness not deeply improved in Phase 4.

## Next (Coordinator)

1. **Cloud Run zero-touch UI cutover** — env vars (`GOOGLE_OAUTH_CLIENT_ID`, `AUTH_DEV_BYPASS=false`, hybrid/citation/BM25 flags), OAuth JS origins, `NEXT_PUBLIC_*` for web, Secret Manager versions.  
2. Re-run live eval hybrid vs dense when corpus is stable.  
3. Phase 6 / backlog items when prioritized (analytics, LB/Armor, multi-turn).  
