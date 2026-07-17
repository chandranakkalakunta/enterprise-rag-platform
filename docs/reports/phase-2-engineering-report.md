# Phase 2 Engineering Report — Ingestion Foundation

**Project:** Enterprise RAG Platform  
**GCP project:** `enterprise-rag-platform-502711`  
**Phase:** 2 — Ingestion & document versioning (MVP lifecycle)  
**Date:** 2026-07-17  
**PR range:** [#11](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/11)–[#15](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/15) + this closure PR  
**Status:** **Complete** — ready for Phase 3 Retrieval  

Related: [Phase 2 retrospective](../retrospectives/phase-2.md)

---

## 1. Deliverables

| Sub-phase | Deliverable | PR |
|-----------|-------------|-----|
| 2.0 | ADR-0006 Firestore Native metadata store | #11 |
| 2.1 | `POST /api/v1/documents/upload` → GCS `raw/` + Firestore | #12 |
| 2.2 | Firestore `(default)` asia-south1 + IAM; extract → ready/failed | #13 |
| 2.3 | Chunking; `processed/` full.txt + chunks.jsonl; CR image ignore | #14 |
| 2.4 | Publish + retire; atomic `active_version_id`; auto-retire previous | #15 |
| Closure | Retro, eng report, backlog tidy, Phase 5 PWA scope | this PR |

---

## 2. MVP lifecycle (implemented)

```text
POST /upload
  → validate PDF|MD ≤50MB
  → gs://…/raw/{document_id}/{version_id}/{filename}
  → Firestore documents/{id} + versions/{id} status=processing
  → extract (markdown | pdfminer.six)
  → chunk (~1000 chars, 150 overlap)
  → gs://…/processed/{document_id}/{version_id}/full.txt
  → gs://…/processed/{document_id}/{version_id}/chunks.jsonl
  → Firestore status=ready | failed (pointers + text_preview only)

POST …/versions/{version_id}/publish
  → ready → published
  → document.active_version_id = version_id
  → previous published active → retired (history kept)

POST …/versions/{version_id}/retire
  → ready | published → retired
  → clear active pointer if needed
```

---

## 3. Key decisions locked in Phase 2

| Decision | Choice |
|----------|--------|
| Metadata store | **Firestore Native** (`asia-south1`) — ADR-0006 |
| Full text location | GCS `processed/`, not Firestore |
| Chunk defaults | 1000 / 150 (tuning backlog BL-ING-03b) |
| Active version | Single `active_version_id` per document |
| Supersede on publish | Previous published → **retired** |
| Cloud Run images | CI-owned; Terraform `lifecycle.ignore_changes` |

---

## 4. Test posture

Backend unit/API tests cover upload validation, extraction, chunking, processed paths (mocked GCS/Firestore), and lifecycle rules (publish/retire 200/400/404/409). Suite size grew through Phase 2 to **70+** tests by Phase 2.4.

---

## 5. Explicitly not in Phase 2 (backlog)

| ID | Item | Notes |
|----|------|-------|
| BL-ING-10 | Async `rag-ingest` worker | Extract/chunk/embed off API path |
| BL-ING-07 | Job visibility API/UI | Operator UX |
| BL-SEC-10 | Real content_admin on ingest | Replaces temp auth |
| BL-ING-08 | Multimodal extract | US-MM-01 |
| BL-ING-03b | Chunk strategy tuning | Evaluation later |
| BL-ING-05 / 06 | Embed + index + alias swap | Phase 3 / retrieval path |
| BL-DEC-05 | Tasks vs Pub/Sub enqueue | ADR when worker lands |

These are **not** Phase 3 incomplete items — they remain general backlog until scheduled.

---

## 6. Phase 5 scope clarification (recorded at Phase 2 close)

**Phase 5** delivers **full PWA** experience:

- Responsive browser UI for **desktop, tablet, and mobile**
- **Installable** PWA (manifest + service worker shell)
- Optional voice (STT/TTS) in the PWA

**Out of scope:** native iOS/Android store apps.

See [ui-specs §7](../ui-specs.md#7-pwa-requirements) and [requirements out-of-scope](../requirements.md).

---

## 7. Readiness for Phase 3

**Green.** Query path can assume:

1. Published versions exist with `active_version_id`.  
2. Chunk text is addressable via `chunks_gcs_uri` / `processed/` prefix.  
3. Metadata is in Firestore; analytics stay on BigQuery.

**Next:** embeddings, Vertex AI Vector Search, hybrid retrieval + RRF, LangGraph query path, citations, guardrails baseline.

---

## 8. Sign-off

Phase 2 (Ingestion MVP lifecycle) is **complete**.  
**Next:** Phase 3 — Hybrid RAG + Guardrails.
