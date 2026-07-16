# Project Backlog — Enterprise RAG Platform

**Living document** — update on every deferral and every completion (with phase/PR).  
**Protocol ref:** §7.7 (Grok Three-Agent Protocol project adaptation)

Last updated: 2026-07-16 (Phase 0 Gamma — requirements lock)

---

## How to use

- Log deferrals the moment they are decided (not only in chat).
- Mark items **Done** with phase + PR link when implemented.
- Group by requirement domain (not a flat unprioritized dump).
- Story IDs: see [requirements.md](./requirements.md); UI: [ui-specs.md](./ui-specs.md).

Status legend: `Todo` | `In Progress` | `Deferred` | `Done` | `Won't Do`

---

## Foundation & Tooling

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-FND-01 | Git monorepo structure, docs, placeholders | Done | Phase 0 | |
| BL-FND-02 | ADR-0001 architecture + ADR-0002 tech stack | Done | Phase 0 | Amended Gamma |
| BL-FND-03 | requirements.md + backlog + protocol | Done | Phase 0 | v3 Gamma lock |
| BL-FND-04 | Terraform skeleton (`var.gcp_project_id`) | Done | Phase 0 | Skeleton only |
| BL-FND-09 | Remove hard-coded GCP project IDs | Done | Phase 0.1 | |
| BL-FND-10 | Detailed requirements v2 + UI specs + arch overview | Done | Phase 0 Beta | |
| BL-FND-11 | ADR-0003 versioning + ADR-0004 guardrails | Done | Phase 0 Beta | |
| BL-FND-12 | Requirements lock Gamma (feedback, MM, LangGraph, security) | Done | Phase 0 Gamma | This change set |
| BL-FND-13 | ADR-0005 security posture (zero JSON keys, WIF) | Done | Phase 0 Gamma | |
| BL-FND-05 | Enable required GCP APIs (idempotent script) | Todo | Phase 1 | |
| BL-FND-06 | CMEK keys + GCS buckets | Todo | Phase 1 | |
| BL-FND-07 | Cloud Build/GHA + WIF keyless CI | Todo | Phase 1–2 | US-OPS-04 |
| BL-FND-08 | detect-secrets in CI | Todo | Phase 1 | |
| BL-FND-14 | Three Cloud Run services (api, ingest-worker, web) | Todo | Phase 1–2 | |
| BL-FND-15 | Health returns version + deployed_at | Todo | Phase 1 | NFR-REL-03a; code change Phase 1 |
| BL-FND-16 | HTTPS LB + Cloud Armor | Deferred | Pre-prod | Explicitly later |

## Auth & Security

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-SEC-01 | Google OAuth + domain allowlist (chandraailabs.com, gmail.com) | Todo | Phase 1 | US-AUTH-01 |
| BL-SEC-02 | Role model: user / content_admin / operator | Todo | Phase 1–2 | |
| BL-SEC-03 | Secret Manager wiring | Todo | Phase 1 | |
| BL-SEC-04 | Non-root Docker images (uid 1001) | Todo | Phase 1 | |
| BL-SEC-05 | PII-free structured logging | Todo | Phase 1 | |
| BL-SEC-06 | Admin action audit log | Todo | Phase 2 | |
| BL-SEC-07 | Custom SAs per service + least privilege | Todo | Phase 1 | ADR-0005 |
| BL-SEC-08 | Enforce zero JSON SA keys in CI/docs/checklists | Todo | Phase 1 | NFR-SEC-10 |

## Ingestion & Versioning

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-ING-01 | Document upload API + GCS storage | Todo | Phase 2 | |
| BL-ING-02 | Parse PDF/DOCX/MD/HTML | Todo | Phase 2 | |
| BL-ING-03 | Chunking strategy + metadata | Todo | Phase 2 | |
| BL-ING-04 | Version publish / retire workflow | Todo | Phase 2 | ADR-0003 |
| BL-ING-05 | Embed + index pipeline on ingest-worker | Todo | Phase 2–3 | |
| BL-ING-06 | Atomic index alias swap on publish | Todo | Phase 3 | |
| BL-ING-07 | Ingest job visibility UI/API | Todo | Phase 2 | |
| BL-ING-08 | Multimodal table/image extraction | Todo | Phase 2–3 | US-MM-01 · P1 |
| BL-ING-09 | Synthetic + OSS fixture corpus | Todo | Phase 2 | Data source policy |

## Retrieval & Generation

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-RAG-01 | Hybrid BM25 + dense retrieval | Todo | Phase 3 | |
| BL-RAG-02 | RRF fusion | Todo | Phase 3 | |
| BL-RAG-03 | Gemini generation with citations | Todo | Phase 3 | |
| BL-RAG-04 | Insufficient-evidence refusal | Todo | Phase 3 | |
| BL-RAG-05 | ACL-aware retrieval | Todo | Phase 3 | |
| BL-RAG-06 | Multi-turn conversation memory | Deferred | Phase 4 | |
| BL-RAG-07 | Collection / filter scope (UX) | Deferred | Phase 4 | US-QA-05 |
| BL-RAG-08 | Optional token streaming to client | Deferred | Phase 3+ | |
| BL-RAG-09 | LangGraph query orchestration | Todo | Phase 3 | P0 · ADR-0002 |
| BL-RAG-10 | Metadata filtering at index query | Todo | Phase 3 | P0 · US-QA-08 |
| BL-RAG-11 | Semantic caching | Todo | Phase 3–4 | P1 · US-QA-07 |
| BL-RAG-12 | Vertex AI Vector Search index wiring | Todo | Phase 2–3 | Locked choice |

## Feedback

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-FB-01 | 5-star feedback API + persistence | Todo | Phase 3 | P0 · US-QA-06 |
| BL-FB-02 | StarRating UI under assistant messages | Todo | Phase 3 | ui-specs §15 |
| BL-FB-03 | Aggregate star analytics | Todo | Phase 6 | US-ANL-05 · P1 |

## Guardrails

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-GRD-01 | Prompt-injection defenses | Todo | Phase 3–4 | |
| BL-GRD-02 | Output grounding / citation checks | Todo | Phase 3–4 | |
| BL-GRD-03 | Configurable safety policies | Deferred | Phase 4 | |
| BL-GRD-04 | Guardrail metrics counters | Todo | Phase 3 | |

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
| BL-ANL-01 | BigQuery query metadata pipeline | Todo | Phase 6 | |
| BL-ANL-02 | Latency percentile dashboards | Todo | Phase 6 | Basic earlier |
| BL-ANL-03 | Held-out evaluation set + quality gate | Todo | Phase 6 | |
| BL-ANL-04 | Token / cost dashboards | Deferred | Phase 6 | |
| BL-ANL-05 | Cache hit metrics | Todo | Phase 3–6 | With semantic cache |

## Frontend

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-FE-01 | Next.js app scaffold beyond placeholder | Todo | Phase 1 | |
| BL-FE-02 | shadcn/ui + app shell per ui-specs | Todo | Phase 1–2 | |
| BL-FE-03 | Chat UI + citations rendering | Todo | Phase 3 | |
| BL-FE-04 | Admin document management UI | Todo | Phase 2–3 | |
| BL-FE-05 | History + settings screens | Todo | Phase 3–4 | |
| BL-FE-06 | Analytics dashboard UI | Todo | Phase 6 | |
| BL-FE-07 | A11y pass on primary flows | Todo | Phase 3+ | |
| BL-FE-08 | Multimodal table/image rendering | Todo | Phase 3–4 | P1 · US-MM-02 |
| BL-FE-09 | Domain-denied login state | Todo | Phase 1 | |

## Open decisions (need ADR soon)

| ID | Decision | Status | Target ADR |
|----|----------|--------|------------|
| BL-DEC-01 | Firestore vs Cloud SQL for metadata | Todo | ADR-0006 |
| BL-DEC-02 | Exact embedding model + dimensions | Todo | ADR-0007 |
| BL-DEC-03 | Vector Search index topology / filter schema | Todo | ADR-0007 |
| BL-DEC-04 | STT/TTS provider selection | Deferred | Phase 5 ADR |
| BL-DEC-05 | Ingest enqueue: Cloud Tasks vs Pub/Sub | Todo | Phase 2 ADR |
| BL-DEC-06 | Semantic cache backing store | Todo | Phase 3 |

**Resolved in Gamma (no longer open):** LangGraph; Vertex AI Vector Search product choice; Cloud Run service split (api / ingest-worker / web); zero JSON keys + WIF posture (ADR-0005).

---

## Recently completed

- **2026-07-16** — Phase 0 Gamma: requirements v3 lock (audience, feedback, multimodal, LangGraph, metadata filters, semantic cache, health version, security); ui-specs + architecture; ADR-0002 amend; ADR-0005.
- **2026-07-16** — Phase 0 Beta: requirements v2, ui-specs, architecture overview, ADR-0003/0004.
- **2026-07-16** — Phase 0.1: project ID parameterization.
- **2026-07-16** — Phase 0 foundation scaffold.
