# Phase 3 Retrospective — Retrieval Foundation

**Date:** 2026-07-19  
**Status:** Complete  
**PR range:** #17 – #22 (ADR-0007/0008 through grounded answer; this closure PR)

## Summary

Phase 3 delivered the first **end-to-end retrieval and grounded answer path**:

**embeddings → Vector Search → dense search API → LangGraph retrieve / evidence check / generate → citations + refusal.**

MVP dense published-only Q&A is live. Hybrid fusion, full guardrails, and UI are explicitly deferred.

## Delivered

| Sub-phase | What |
|-----------|------|
| **3.0** | ADR-0007 (Vertex embeddings + Vector Search lifecycle) · ADR-0008 (LangGraph retrieve → check → generate) |
| **3.1** | Embed on version ready → `processed/.../embeddings.jsonl`; `embeddings_status` independent of content status |
| **3.2** | STREAM_UPDATE Vector Search (dev-sized); upsert `active=false`; publish/retire activate/deactivate |
| **3.2 hotfix** | Bootstrap `datapoint.json` (never `.keep`) for `contents_delta_uri` |
| **3.3** | `POST /api/v1/query/search` — active-only dense neighbors |
| **3.4** | `POST /api/v1/query/answer` — grounded Gemini + citations + minimal refusal |

Also: modular services, runbooks, unit/API tests with mocked Vertex clients.

## Lessons

1. **Vector Search bootstrap must be valid embedding JSON** (e.g. `.json` / `.csv` / `.avro`) — never `.keep` or extensionless markers; Vertex returns `FAILED_PRECONDITION` / unknown format otherwise (Phase 3.2 hotfix).  
2. **Targeted Terraform applies** can leave stale outputs or partial state; refresh-only / re-apply bootstrap+index targets carefully rather than destroying unrelated infra.  
3. **Separating `embeddings_status` from content `status`** kept extract/chunk failures debuggable without blocking “ready” text artifacts.  
4. **Published-only `active=true` filter** is the right default for enterprise RAG (audit + single active version).  
5. **Simple LangGraph** (few nodes) was enough for MVP; hybrid/cache can extend the graph later without rewriting the product contract.

## Deferred (backlog — not incomplete Phase 3 MVP)

| ID / theme | Item |
|------------|------|
| BL-RAG-01 / 02 | Hybrid BM25 + RRF fusion |
| BL-RAG-11 / BL-DEC-06 | Semantic cache |
| BL-GRD-* | Full multi-layer guardrail stack |
| BL-RAG-16 | Inactive vector hard-delete job (30–90d retention) |
| BL-ING-10 | Async worker for embed/upsert |
| — | Live E2E wiring hardening / eval smoke |
| BL-FE-* / Phase 5 | Chat UI, admin UI, full PWA |

## Residual risks (carry forward)

- Sync embed / upsert / generate still on `rag-api` (latency at scale).  
- Temp auth (Bearer / dev bypass) on query and ingest.  
- Live Vector Search + Gemini env wiring and cost for always-on endpoint.  
- Model can still over-claim despite prompt + minimal evidence gate.

## Next (Coordinator order)

1. **Phase 5** — full responsive **PWA / UI** (desktop/tablet/mobile browser + installable; **no native apps**).  
2. **Phase 4** — RAG quality (hybrid/RRF, multi-turn, ACL depth, fuller guardrails).  

Phase numbers stay as named tracks; **delivery order** is **5 then 4**.
