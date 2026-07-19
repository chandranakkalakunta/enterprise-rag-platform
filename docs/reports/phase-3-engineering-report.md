# Phase 3 Engineering Report — Retrieval Foundation

**Project:** Enterprise RAG Platform  
**GCP project:** `enterprise-rag-platform-502711`  
**Phase:** 3 — Retrieval + grounded Q&A (MVP dense path)  
**Date:** 2026-07-19  
**PR range:** [#17](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/17)–[#22](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/22) + this closure PR  
**Status:** **Complete** — next delivery track **Phase 5 (PWA/UI)**, then **Phase 4 (RAG quality)**  

Related: [Phase 3 retrospective](../retrospectives/phase-3.md)

---

## 1. Deliverables

| Sub-phase | Deliverable | PR |
|-----------|-------------|-----|
| 3.0 | ADR-0007 embeddings/Vector Search; ADR-0008 retrieval/generation | #17 |
| 3.1 | Embed on ready → `embeddings.jsonl`; `embeddings_status` | #18 |
| 3.2 | Vector Search STREAM_UPDATE index; upsert + activate/deactivate | #19 |
| 3.2 hotfix | Bootstrap `datapoint.json` (not `.keep`) | #20 |
| 3.3 | `POST /api/v1/query/search` dense active-only search | #21 |
| 3.4 | `POST /api/v1/query/answer` LangGraph + Gemini + citations + refusal | #22 |
| Closure | Retro, eng report, backlog tidy, next-order Phase 5→4 | this PR |

---

## 2. MVP path (implemented)

```text
Version ready
  → embed chunks → GCS embeddings.jsonl
  → Vector Search upsert (active=false)

Publish
  → Firestore published + active_version_id
  → re-upsert active=true; previous published active=false

POST /api/v1/query/search
  → embed query → FindNeighbors (active=true [+ collection])

POST /api/v1/query/answer
  → retrieve → evidence_check → Gemini (temp 0.2) → answer + citations
  → refuse if no usable evidence
```

---

## 3. Key decisions locked

| Decision | Choice |
|----------|--------|
| Embeddings | Vertex `EMBEDDING_MODEL_ID` (default `text-embedding-005`, 768-d) |
| Index | Vertex Vector Search STREAM_UPDATE; filters `active`, `collection`, `document_id`, `version_id` |
| Lifecycle | Embed on ready; activate on publish; deactivate on retire (`active` flag; hard-delete backlog) |
| Query | Dense published-only; top_k default **5** |
| Generation | Gemini `GENERATION_MODEL_ID` (default `gemini-2.0-flash-001`); temp **0.2** |
| Orchestration | Simple **LangGraph** graph |
| Bootstrap | Valid **datapoint.json** under `contents_delta_uri` — never `.keep` |

---

## 4. Test posture

Backend suite grew through Phase 3 to **110+** tests: embeddings, vector datapoint shape, search API, evidence gate, answer success/refusal, lifecycle — all with mocked GCP clients.

---

## 5. Explicitly not Phase 3 MVP (remain open)

| ID | Item | Target |
|----|------|--------|
| BL-RAG-01 / 02 | Hybrid BM25 + RRF | Phase 4 |
| BL-RAG-11 / BL-DEC-06 | Semantic cache | Phase 4+ |
| BL-GRD-* | Full guardrail stack | Phase 4 |
| BL-RAG-16 | Inactive vector hard-delete | Backlog |
| BL-ING-10 | Async embed/upsert worker | Backlog |
| Live E2E hardening | Env wiring / eval smoke | Backlog / ops |
| BL-FE-* | Chat/admin UI | **Phase 5** |

Do not treat these as incomplete Phase 3 acceptance criteria.

---

## 6. Delivery order after Phase 3

| Order | Phase | Focus |
|-------|-------|--------|
| **1 (next)** | **5** | Full responsive PWA/UI (no native apps); consume search/answer APIs |
| **2** | **4** | RAG quality: hybrid/RRF, multi-turn, ACL depth, fuller guards |
| Later | **6** | Analytics, eval gates, Binary Auth |

---

## 7. Sign-off

Phase 3 (Retrieval Foundation MVP) is **complete**.  
**Next major track:** Phase 5 — full PWA / UI design and implementation.
