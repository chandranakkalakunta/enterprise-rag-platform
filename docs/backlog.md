# Project Backlog — Enterprise RAG Platform

**Living document** — update on every deferral and every completion (with phase/PR).  
**Protocol ref:** §7.7 (Grok Three-Agent Protocol project adaptation)

Last updated: 2026-07-19 (**Phase 3 Complete** — next delivery: Phase 5 PWA, then Phase 4 RAG quality)

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
| BL-FND-01 | Git monorepo structure, docs, placeholders | Done | ✓ Done — Phase 0 / PR #1 | |
| BL-FND-02 | ADR-0001 architecture + ADR-0002 tech stack | Done | ✓ Done — Phase 0 / PR #1 | |
| BL-FND-03 | requirements.md + backlog + protocol | Done | ✓ Done — Phase 0 / PR #1 | v3 Gamma lock |
| BL-FND-04 | Terraform skeleton (`var.gcp_project_id`) | Done | ✓ Done — Phase 0 / PR #1 | Skeleton only |
| BL-FND-09 | Parameterize GCP project IDs (no hard-code in app) | Done | ✓ Done — Phase 0 / PR #1 | Placeholders + var.gcp_project_id |
| BL-FND-18 | Switch GCP project example to `enterprise-rag-platform-502711` | Done | ✓ Done — Phase 0.1 / PR #2 | Project number 642114828076 |
| BL-FND-10 | Detailed requirements v2 + UI specs + arch overview | Done | ✓ Done — Phase 0 Beta / PR #1 | |
| BL-FND-11 | ADR-0003 versioning + ADR-0004 guardrails | Done | ✓ Done — Phase 0 Beta / PR #1 | |
| BL-FND-12 | Requirements lock Gamma (feedback, MM, LangGraph, security) | Done | ✓ Done — Phase 0 Gamma / PR #1 | |
| BL-FND-13 | ADR-0005 security posture (zero JSON keys, WIF) | Done | ✓ Done — Phase 0 Gamma / PR #1 | |
| BL-FND-17 | Phase 0 closure (retro, eng report, README, phases index) | Done | ✓ Done — Phase 0 / PR #1 | Closure commit |
| BL-FND-05 | Enable required GCP APIs (Terraform for_each) | Done | ✓ Done — Phase 1.1 / PR #3 | 13 services; billing required |
| BL-FND-19 | Multi-env Terraform layout (dev/test/prod) | Done | ✓ Done — Phase 1.1 / PR #3 | tfvars + backend.hcl |
| BL-FND-20 | State buckets enterprise-rag-tfstate-{dev,test,prod} | Done | ✓ Done — Phase 1.1 / PR #3 | versioning, UBLA, soft-delete 7d |
| BL-FND-21 | Remote state migration to GCS (dev backend) | Done | ✓ Done — Phase 1.1 / PR #3 | gs://enterprise-rag-tfstate-dev |
| BL-FND-06 | CMEK keyring + crypto keys (gcs + secrets) | Done | ✓ Done — Phase 1.3 / PR #5 | rag-keyring / rag-*-key |
| BL-FND-06b | Data GCS buckets with CMEK (`rag-docs-*`) | Done | ✓ Done — Phase 1.4 / PR #6 | versioning, lifecycle 90d, UBLA |
| BL-FND-07 | Cloud Build/GHA + WIF keyless CI (pool + provider + SA) | Done | ✓ Done — Phase 1.2 / PR #4 | Identity foundation |
| BL-FND-08 | detect-secrets in CI | Todo | Post–Phase 2 | Residual follow-up |
| BL-FND-32 | Phase 2 closure (retro, eng report, backlog tidy) | Done | ✓ Done — Phase 2 closure | |
| BL-FND-33 | Phase 3 closure (retro, eng report, next-order 5→4) | Done | ✓ Done — Phase 3 closure | |
| BL-FND-14 | Three Cloud Run services (rag-api, rag-ingest, rag-web) | Done | ✓ Done — Phase 1.6 / PR #8 | Stubs + SAs |
| BL-FND-15 | Health returns version + deployed_at | Done | ✓ Done — Phase 1.5 / PR #7 | APP_VERSION / DEPLOYED_AT |
| BL-FND-16 | HTTPS LB + Cloud Armor | Deferred | Pre-prod | Explicitly later |
| BL-FND-22 | Custom SAs per service (api/ingest/web/ci) | Done | ✓ Done — Phase 1.2 / PR #4 | ADR-0005 |
| BL-FND-23 | WIF GitHub OIDC + workloadIdentityUser on sa-rag-ci | Done | ✓ Done — Phase 1.2 / PR #4 | Repo-restricted |
| BL-FND-24 | Remove project-level storage.admin from sa-rag-ci | Done | ✓ Done — Phase 1.5 / PR #7 | Bucket objectAdmin remains |
| BL-FND-25 | OAuth secret shells + CMEK | Done | ✓ Done — Phase 1.3 / PR #5 | Empty versions; Coordinator fills |
| BL-FND-26 | Binary Authorization for Cloud Run images | Todo | **P1 / Phase 6+** | Supply-chain hardening; NFR-SEC-14 |
| BL-FND-27 | Docs prefix convention (raw/versions/assets/processed) | Done | ✓ Done — Phase 1.4 / PR #6 | Documented in runbook |
| BL-FND-28 | Replace Cloud Run stub images with real app images | Done | ✓ Done — Phase 1.7 / PR #9 | CI deploys rag-api image |
| BL-FND-29 | GitHub Actions CI workflow (test → build → deploy) | Done | ✓ Done — Phase 1.7 / PR #9 | `.github/workflows/ci.yml` |
| BL-FND-30 | Artifact Registry `rag-containers` | Done | ✓ Done — Phase 1.7 / PR #9 | asia-south1 DOCKER |
| BL-FND-31 | Phase 1 closure (retro, eng report, living docs) | Done | ✓ Done — Phase 1 / this PR | |

## Auth & Security

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-SEC-01 | Google OAuth + domain allowlist (chandraailabs.com, gmail.com) | Todo | Backlog (post–Phase 2) | Spec documented Phase 1.6; not Phase 3 gate |
| BL-SEC-02 | Role model: user / content_admin / operator | Todo | Backlog (post–Phase 2) | |
| BL-SEC-03 | Secret Manager shells + CMEK | Done | ✓ Done — Phase 1.3 / PR #5 | Values via runbook later |
| BL-SEC-04 | Non-root Docker images (uid 1001) | Done | ✓ Done — Phase 1.7 / PR #9 | API Dockerfile |
| BL-SEC-05 | PII-free structured logging | Todo | Backlog | Baseline JSON logging exists |
| BL-SEC-06 | Admin action audit log | Todo | Backlog | |
| BL-SEC-07 | Custom SAs per service + least privilege | Done | ✓ Done — Phase 1.2 / PR #4 | Baseline roles |
| BL-SEC-08 | Enforce zero JSON SA keys (WIF only for CI) | Done | ✓ Done — Phase 1.2 / PR #4 | NFR-SEC-10 |
| BL-SEC-09 | **Binary Authorization for Cloud Run** | Todo | **P1 / Phase 6+** | NFR-SEC-14; deferred supply-chain hardening |
| BL-SEC-10 | **Real content_admin auth on ingest endpoints** | Todo | **Backlog** (was Phase 2 residual) | Replace AUTH_DEV_BYPASS / Bearer stub on upload/publish/retire |

## Ingestion & Versioning

### Phase 2 MVP — complete

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-ING-01 | Document upload API + GCS storage | Done | ✓ Done — Phase 2.1 | POST /api/v1/documents/upload |
| BL-ING-02a | Firestore Native DB + IAM (api/ingest) | Done | ✓ Done — Phase 2.2 | asia-south1; roles/datastore.user |
| BL-ING-02b | Version status processing→ready/failed | Done | ✓ Done — Phase 2.2 | Sync extraction in API; module worker-ready |
| BL-ING-03 | Chunking + processed/ GCS storage | Done | ✓ Done — Phase 2.3 | full.txt + chunks.jsonl; Firestore pointers only |
| BL-ING-03c | Cloud Run TF lifecycle ignore (CI-owned images) | Done | ✓ Done — Phase 2.3 | ignore_changes on template containers |
| BL-ING-04 | Version publish / retire workflow | Done | ✓ Done — Phase 2.4 | publish/retire APIs; auto-retire previous published |

### Moved from Phase 2 residual → living backlog (not Phase 3 scope)

| ID | Item | Status | Target | Notes |
|----|------|--------|--------|-------|
| BL-ING-10 | **Async ingest worker (`rag-ingest`)** | Todo | **Backlog** | Move extract/chunk/embed off API; enqueue per BL-DEC-05 |
| BL-ING-07 | **Ingest job visibility UI/API** | Todo | **Backlog** | Operator job status; not a Phase 3 gate |
| BL-ING-02 | Parse DOCX/HTML (+ full matrix beyond PDF/MD) | Todo | **Backlog** | PDF+MD done in Phase 2.2; real auth on ingest: BL-SEC-10 |
| BL-ING-03b | **Chunking strategy tuning** | Todo | **Backlog** | Defaults 1000/150; evaluate later |
| BL-ING-08 | Multimodal table/image extraction | Todo | **Backlog** / Phase 3–4 | US-MM-01 · P1 |
| BL-ING-09 | Synthetic + OSS fixture corpus | Todo | **Backlog** | Eval fixtures |
| BL-ING-05 | Embed + index pipeline | Todo | **Phase 3** | With retrieval path |
| BL-ING-06 | Atomic index alias swap on publish | Todo | **Phase 3+** | After Vector Search wiring |

## Retrieval & Generation

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-RAG-13 | **ADR-0007 + ADR-0008** retrieval foundation decisions | Done | ✓ Done — Phase 3.0 | Embed/VS lifecycle + LangGraph MVP flow |
| BL-RAG-14a | Embed on ready → `embeddings.jsonl` + Firestore fields | Done | ✓ Done — Phase 3.1 | Content ready independent of embed failure |
| BL-RAG-14b | Activate/deactivate index on publish/retire | Done | ✓ Done — Phase 3.2 | active=true/false re-upsert; no re-embed |
| BL-RAG-12 | Vertex AI Vector Search index + endpoint wiring | Done | ✓ Done — Phase 3.2 | STREAM_UPDATE; upsert active=false on ready |
| BL-RAG-16 | **Hard-delete inactive vectors after retention (30–90d)** | Todo | **Backlog** | Retire sets active=false only; scheduled cleanup job |
| BL-RAG-15a | Dense search API `POST /api/v1/query/search` | Done | ✓ Done — Phase 3.3 | active=true only; top_k default 5 |
| BL-RAG-09 | LangGraph query orchestration (simple graph) | Done | ✓ Done — Phase 3.4 | retrieve → evidence → generate/refuse |
| BL-RAG-15 | Grounded answer API `POST /api/v1/query/answer` | Done | ✓ Done — Phase 3.4 | Answer + citations + refusal |
| BL-RAG-03 | Gemini generation with citations | Done | ✓ Done — Phase 3.4 | `GENERATION_MODEL_ID`, temp 0.2 |
| BL-RAG-04 | Insufficient-evidence refusal (minimal) | Done | ✓ Done — Phase 3.4 | Zero hits / empty text / optional min score |
| BL-RAG-10 | Metadata filtering at index (published/active) | Done | ✓ Done — Phase 3.2–3.3 | active=true on upsert/query |
### Phase 3 MVP complete — remaining retrieval quality (not incomplete Phase 3)

| ID | Item | Status | Target | Notes |
|----|------|--------|--------|-------|
| BL-RAG-01 | Hybrid BM25 + dense retrieval | Todo | **Phase 4** | Deferred by ADR-0008 |
| BL-RAG-02 | RRF fusion | Todo | **Phase 4** | Deferred by ADR-0008 |
| BL-RAG-05 | ACL-aware retrieval (deep) | Todo | **Phase 4** | Beyond published-only |
| BL-RAG-06 | Multi-turn conversation memory | Deferred | **Phase 4** | |
| BL-RAG-07 | Collection / filter scope (UX) | Deferred | **Phase 4 / 5** | US-QA-05 |
| BL-RAG-08 | Optional token streaming to client | Deferred | Phase 4+ | |
| BL-RAG-11 | Semantic caching | Todo | **Phase 4** | P1 · BL-DEC-06 |
| BL-RAG-17 | Live E2E wiring / eval smoke (search+answer) | Todo | **Backlog** | Ops hardening after UI exists |
| BL-ING-10 | Async worker for embed/upsert | Todo | **Backlog** | Offload from rag-api |

## Feedback

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-FB-01 | 5-star feedback API + persistence | Todo | **Phase 5** (with chat UI) | P0 · US-QA-06 |
| BL-FB-02 | StarRating UI under assistant messages | Todo | **Phase 5** | ui-specs §15 |
| BL-FB-03 | Aggregate star analytics | Todo | Phase 6 | US-ANL-05 · P1 |

## Guardrails

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-GRD-01 | Prompt-injection defenses | Todo | **Phase 4** | MVP = minimal evidence gate only |
| BL-GRD-02 | Output grounding / citation checks | Todo | **Phase 4** | |
| BL-GRD-03 | Configurable safety policies | Deferred | **Phase 4** | |
| BL-GRD-04 | Guardrail metrics counters | Todo | **Phase 4+** | |

## Voice & PWA (Phase 5 = full PWA; no native apps)

**Scope lock:** Phase 5 delivers responsive **desktop / tablet / mobile browser** UX plus **installable PWA**. Native App Store / Play Store apps are **out of scope**.

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-VOICE-01 | STT integration | Deferred | Phase 5 | In-PWA only |
| BL-VOICE-02 | TTS integration | Deferred | Phase 5 | In-PWA only |
| BL-PWA-01 | Installable PWA shell (manifest + SW) | Todo | **Phase 5 (next)** | Desktop/tablet/mobile browser |
| BL-PWA-02 | Offline UI shell | Todo | **Phase 5** | P2; shell only, not offline RAG |
| BL-PWA-03 | Responsive desktop/tablet/mobile layouts | Todo | **Phase 5 (next)** | Full PWA profile |

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
| BL-FE-01 | Next.js app scaffold beyond placeholder | Todo | **Phase 5 (next)** | |
| BL-FE-02 | shadcn/ui + app shell per ui-specs | Todo | **Phase 5 (next)** | Spec locked Phase 0 |
| BL-FE-03 | Chat UI + citations rendering | Todo | **Phase 5 (next)** | Calls `/query/answer` + `/query/search` |
| BL-FE-04 | Admin document management UI | Todo | **Phase 5** | Upload/publish APIs already exist |
| BL-FE-05 | History + settings screens | Todo | **Phase 5** | |
| BL-FE-06 | Analytics dashboard UI | Todo | Phase 6 | |
| BL-FE-07 | A11y pass on primary flows | Todo | **Phase 5** | |
| BL-FE-08 | Multimodal table/image rendering | Todo | Phase 4–5 | P1 · US-MM-02 |
| BL-FE-09 | Domain-denied login state | Todo | **Phase 5** (with OAuth) | |

## Open decisions (need ADR soon)

| ID | Decision | Status | Target ADR |
|----|----------|--------|------------|
| BL-DEC-01 | Firestore vs Cloud SQL for metadata | Done | ✓ Done — Phase 2.0 / ADR-0006 | **Firestore Native** |
| BL-DEC-02 | Embedding provider + model config + lifecycle | Done | ✓ Done — Phase 3.0 / ADR-0007 | Vertex; `EMBEDDING_MODEL_ID`; embed on ready |
| BL-DEC-03 | Vector Search index + chunk payload + filters | Done | ✓ Done — Phase 3.0 / ADR-0007 | Vertex AI Vector Search |
| BL-DEC-07 | Retrieval/gen flow + knobs (top_k, temperature) | Done | ✓ Done — Phase 3.0 / ADR-0008 | LangGraph MVP; temp 0.2; top_k 5 |
| BL-DEC-04 | STT/TTS provider selection | Deferred | Phase 5 ADR | |
| BL-DEC-05 | Ingest enqueue: Cloud Tasks vs Pub/Sub | Todo | Backlog ADR (with BL-ING-10) | |
| BL-DEC-06 | Semantic cache backing store | Todo | **Phase 4** | Deferred with hybrid/cache |

**Resolved in Phase 0–1:** LangGraph; Vertex AI Vector Search product; Cloud Run split; zero JSON keys + WIF; audience allowlist; CMEK; CI.  
**Resolved in Phase 2:** Firestore metadata; MVP ingest lifecycle.  
**Resolved in Phase 3:** Dense retrieval MVP + grounded answer (3.0–3.4); hybrid/RRF/full guards/hard-delete remain backlog.  
**Delivery order after Phase 3:** **Phase 5 (PWA/UI) → Phase 4 (RAG quality) → Phase 6.**  
**Phase 5 scope:** Full PWA only — no native apps.

---

## Recently completed

- **2026-07-19** — **Phase 3 complete:** retrospective + engineering report; next track Phase 5 then Phase 4.
- **2026-07-19** — **Phase 3.4:** Grounded answer `POST /api/v1/query/answer` (LangGraph + Gemini + citations + refusal).
- **2026-07-19** — **Phase 3.3:** Dense search API `POST /api/v1/query/search` (active-only neighbors; no generation).
- **2026-07-18** — **Phase 3.2:** Vector Search index (dev STREAM_UPDATE); upsert on ready; activate/deactivate on publish/retire; BL-RAG-16 hard-delete backlog.
- **2026-07-18** — **Phase 3.1:** Vertex embed on ready; `processed/.../embeddings.jsonl`; `embeddings_status` on version.
- **2026-07-18** — **Phase 3.0:** ADR-0007 (embeddings + Vector Search) + ADR-0008 (retrieval + grounded generation) accepted.
- **2026-07-17** — **Phase 2 complete:** retrospective + engineering report; residual items moved to backlog; Phase 5 PWA scope clarified.
- **2026-07-17** — **Phase 2.4:** Publish + retire endpoints; atomic active_version_id; previous published auto-retired; strict 409 transitions; tests + runbook.
- **2026-07-17** — **Phase 2.3:** Chunking (1000/150); processed/ full.txt + chunks.jsonl; Firestore preview/pointers only; Cloud Run image lifecycle ignore.
- **2026-07-17** — **Phase 2.2:** Firestore DB `(default)` asia-south1 + IAM; Markdown/PDF extraction; status `ready`/`failed`; tests + runbooks.
- **2026-07-17** — **Phase 2.1:** Upload API — multipart PDF/MD ≤50MB to GCS `raw/`, Firestore Document + Version subcollection (`processing`); temp auth; tests + runbook.
- **2026-07-17** — **Phase 2.0:** ADR-0006 accepted — Firestore (Native mode) as long-term metadata store.
- **2026-07-17** — **Phase 1 complete:** retrospective + engineering report; all Phase 1 foundation items Done (PRs #3–#9).
- **2026-07-17** — **Phase 1.7:** GHA CI + WIF deploy; Artifact Registry `rag-containers`; API Dockerfile; deploy to `rag-api` on main.
- **2026-07-17** — **Phase 1.6:** Cloud Run stubs; OAuth allowlist + Binary Auth tracking.
- **2026-07-17** — **Phase 1.5:** Health endpoints; removed project `storage.admin` from sa-rag-ci.
- **2026-07-17** — **Phase 1.4:** `rag-docs-*` with CMEK and bucket IAM.
- **2026-07-17** — **Phase 1.3:** CMEK keyring + Secret Manager shells.
- **2026-07-17** — **Phase 1.2:** SAs + WIF.
- **2026-07-17** — **Phase 1.1:** Multi-env Terraform + APIs + state buckets.
