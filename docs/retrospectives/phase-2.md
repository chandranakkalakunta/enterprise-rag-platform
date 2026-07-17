# Phase 2 Retrospective — Ingestion Foundation

**Date:** 2026-07-17  
**Status:** Complete  
**PR range:** #11 – #15 (ADR-0006 through publish/retire; this closure PR)

## Summary

Phase 2 delivered a complete MVP document lifecycle:

**upload → extract → chunk → store processed artifacts → publish / retire.**

Product-meaningful versioning is live before retrieval work begins.

## Delivered

| Sub-phase | What |
|-----------|------|
| **2.0** | ADR-0006 — Firestore Native as long-term metadata store |
| **2.1** | Upload API (PDF + Markdown, ≤50MB) → GCS `raw/` + Firestore Document/Version |
| **2.2** | Firestore DB + IAM; Markdown + pdfminer.six extraction; status `ready` / `failed` |
| **2.3** | Chunking (1000/150); GCS `processed/` (`full.txt`, `chunks.jsonl`); slim Firestore pointers; Cloud Run image lifecycle ignore |
| **2.4** | Publish + retire APIs; atomic `active_version_id`; auto-retire previous published version |

Also: unit/API tests, runbooks, modular extraction/chunking/lifecycle services.

## Moved to backlog (not incomplete Phase 3)

These were **explicitly deferred** out of Phase 2 MVP scope — they remain backlog items, not Phase 3 acceptance criteria:

| ID | Item |
|----|------|
| BL-ING-10 | Async ingest worker (`rag-ingest`) for extract/chunk/embed |
| BL-ING-07 | Ingest job visibility UI/API |
| BL-SEC-10 | Real `content_admin` auth on ingest endpoints (replace temp Bearer/bypass) |
| BL-ING-08 | Multimodal tables/images (already deferred) |
| BL-ING-03b | Chunk strategy tuning (already tracked) |
| BL-ING-02 | Full parse matrix (DOCX/HTML beyond PDF/MD) |
| BL-DEC-05 | Ingest enqueue: Cloud Tasks vs Pub/Sub |
| BL-ING-05 / BL-ING-06 | Embed + index + alias swap (belong with retrieval / later hardening) |

## Lessons

1. **Modular extract/chunk** (no FastAPI/GCS/Firestore in pure modules) makes later worker migration straightforward.  
2. **Slim Firestore** (pointers + preview only; full text in GCS) was the right call for the 1 MiB document limit and ops simplicity.  
3. Completing **publish/retire** before retrieval gives a product-meaningful lifecycle and clear `active_version_id` semantics for Phase 3 query path.  
4. **Targeted Terraform apply / lifecycle ignore** on Cloud Run images avoids CI vs IaC fights.

## Residual risks (carry forward)

- Sync extract/chunk still runs in API (latency/timeout risk on large PDFs).  
- Temp auth only on upload/publish/retire.  
- No embed/index yet — published ≠ retrievable until Phase 3.  
- `rag-ingest` still a stub service.

## Ready for Phase 3

**Yes** — embeddings + Vertex AI Vector Search + first hybrid query path, grounded on published versions only.
