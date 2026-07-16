# Project Backlog — Enterprise RAG Platform

**Living document** — update on every deferral and every completion (with phase/PR).  
**Protocol ref:** §7.7 (Grok Three-Agent Protocol project adaptation)

Last updated: 2026-07-16 (Phase 0.1 — project ID parameterization)

---

## How to use

- Log deferrals the moment they are decided (not only in chat).
- Mark items **Done** with phase + PR link when implemented.
- Group by requirement domain (not a flat unprioritized dump).

Status legend: `Todo` | `In Progress` | `Deferred` | `Done` | `Won't Do`

---

## Foundation & Tooling

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-FND-01 | Git monorepo structure, docs, placeholders | Done | Phase 0 | This PR |
| BL-FND-02 | ADR-0001 architecture + ADR-0002 tech stack | Done | Phase 0 | This PR |
| BL-FND-03 | requirements.md + backlog + protocol | Done | Phase 0 | This PR |
| BL-FND-04 | Terraform skeleton (`var.gcp_project_id`) | Done | Phase 0 | Skeleton only; no apply yet |
| BL-FND-09 | Remove hard-coded GCP project IDs from docs/TF | Done | Phase 0.1 | Use `var.gcp_project_id` + placeholders |
| BL-FND-05 | Enable required GCP APIs (idempotent script) | Todo | Phase 1 | List APIs in runbook |
| BL-FND-06 | CMEK keys + GCS buckets | Todo | Phase 1 | Non-negotiable early |
| BL-FND-07 | Cloud Build + WIF keyless CI | Todo | Phase 1–2 | |
| BL-FND-08 | detect-secrets in CI | Todo | Phase 1 | |

## Auth & Security

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-SEC-01 | Google OAuth login (US-AUTH-01) | Todo | Phase 1 | |
| BL-SEC-02 | Role model: user / content_admin / operator | Todo | Phase 1–2 | |
| BL-SEC-03 | Secret Manager wiring for app secrets | Todo | Phase 1 | |
| BL-SEC-04 | Non-root Docker images (uid 1001) | Todo | Phase 1 | |
| BL-SEC-05 | PII-free structured logging | Todo | Phase 1 | |

## Ingestion & Versioning

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-ING-01 | Document upload API + GCS storage | Todo | Phase 2 | |
| BL-ING-02 | Parse PDF/DOCX/MD/HTML | Todo | Phase 2 | |
| BL-ING-03 | Chunking strategy + metadata | Todo | Phase 2 | ADR expected |
| BL-ING-04 | Version publish / retire workflow | Todo | Phase 2 | |
| BL-ING-05 | Embed + index pipeline (async) | Todo | Phase 2–3 | |
| BL-ING-06 | Atomic index alias swap on publish | Deferred | Phase 3 | From ADR-0001 risk |

## Retrieval & Generation

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-RAG-01 | Hybrid BM25 + dense retrieval | Todo | Phase 3 | |
| BL-RAG-02 | RRF fusion | Todo | Phase 3 | |
| BL-RAG-03 | Gemini generation with citations | Todo | Phase 3 | |
| BL-RAG-04 | Insufficient-evidence refusal | Todo | Phase 3 | |
| BL-RAG-05 | ACL-aware retrieval | Todo | Phase 3 | |
| BL-RAG-06 | Multi-turn conversation memory | Deferred | Phase 4 | US-QA-04 |
| BL-RAG-07 | Collection / filter scope | Deferred | Phase 4 | US-QA-05 |

## Guardrails

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-GRD-01 | Prompt-injection defenses | Todo | Phase 3–4 | |
| BL-GRD-02 | Output grounding checks | Todo | Phase 3–4 | |
| BL-GRD-03 | Configurable safety policies | Deferred | Phase 4 | US-GRD-04 |

## Voice & PWA

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-VOICE-01 | STT integration | Deferred | Phase 5 | |
| BL-VOICE-02 | TTS integration | Deferred | Phase 5 | |
| BL-PWA-01 | Installable PWA shell | Deferred | Phase 5 | |
| BL-PWA-02 | Offline UI shell | Deferred | Phase 5 | P2 |

## Analytics & Evaluation

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-ANL-01 | BigQuery query metadata pipeline (no raw PII) | Todo | Phase 6 | |
| BL-ANL-02 | Latency percentile dashboards | Todo | Phase 6 | Basic metrics earlier |
| BL-ANL-03 | Held-out evaluation set + quality gate | Todo | Phase 6 | Never train on test |
| BL-ANL-04 | Token / cost dashboards | Deferred | Phase 6 | |

## Frontend

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-FE-01 | Next.js app scaffold beyond placeholder | Todo | Phase 1 | |
| BL-FE-02 | Chat UI + citations rendering | Todo | Phase 3 | |
| BL-FE-03 | Admin document management UI | Todo | Phase 2–3 | |

## Open decisions (need ADR soon)

| ID | Decision | Status | Target ADR |
|----|----------|--------|------------|
| BL-DEC-01 | Firestore vs Cloud SQL for metadata | Todo | ADR-0003 |
| BL-DEC-02 | Exact embedding model + dimensions | Todo | ADR-0004 |
| BL-DEC-03 | Vector Search vs alternative managed index | Todo | ADR-0004 |
| BL-DEC-04 | STT/TTS provider selection | Deferred | Phase 5 ADR |

---

## Recently completed

- **2026-07-16** — Phase 0.1: removed hard-coded GCP project IDs; Terraform `var.gcp_project_id` + placeholders only.
- **2026-07-16** — Phase 0 foundation: repo structure, requirements, ADRs 0001–0002, protocol, Terraform skeleton, placeholders.
