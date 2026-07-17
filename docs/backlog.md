# Project Backlog — Enterprise RAG Platform

**Living document** — update on every deferral and every completion (with phase/PR).  
**Protocol ref:** §7.7 (Grok Three-Agent Protocol project adaptation)

Last updated: 2026-07-17 (**Phase 1 complete** — foundation closed)

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
| BL-FND-08 | detect-secrets in CI | Todo | Phase 2+ | Residual follow-up |
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
| BL-SEC-01 | Google OAuth + domain allowlist (chandraailabs.com, gmail.com) | Todo | Phase 2 | Spec documented Phase 1.6 |
| BL-SEC-02 | Role model: user / content_admin / operator | Todo | Phase 2 | |
| BL-SEC-03 | Secret Manager shells + CMEK | Done | ✓ Done — Phase 1.3 / PR #5 | Values via runbook later |
| BL-SEC-04 | Non-root Docker images (uid 1001) | Done | ✓ Done — Phase 1.7 / PR #9 | API Dockerfile |
| BL-SEC-05 | PII-free structured logging | Todo | Phase 2 | Baseline JSON logging exists |
| BL-SEC-06 | Admin action audit log | Todo | Phase 2 | |
| BL-SEC-07 | Custom SAs per service + least privilege | Done | ✓ Done — Phase 1.2 / PR #4 | Baseline roles |
| BL-SEC-08 | Enforce zero JSON SA keys (WIF only for CI) | Done | ✓ Done — Phase 1.2 / PR #4 | NFR-SEC-10 |
| BL-SEC-09 | **Binary Authorization for Cloud Run** | Todo | **P1 / Phase 6+** | NFR-SEC-14; deferred supply-chain hardening |

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
| BL-ING-09 | Synthetic + OSS fixture corpus | Todo | Phase 2 | |

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
| BL-RAG-12 | Vertex AI Vector Search index wiring | Todo | Phase 2–3 | Locked product choice |

## Feedback

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-FB-01 | 5-star feedback API + persistence | Todo | Phase 3 | P0 · US-QA-06 |
| BL-FB-02 | StarRating UI under assistant messages | Todo | Phase 3 | ui-specs §15 |
| BL-FB-03 | Aggregate star analytics | Todo | Phase 6 | US-ANL-05 · P1 |

## Guardrails

| ID | Item | Status | Phase / PR | Notes |
|----|------|--------|------------|-------|
| BL-GRD-01 | Prompt-injection defenses | Todo | Phase 3–4 | Spec locked Phase 0 |
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
| BL-FE-01 | Next.js app scaffold beyond placeholder | Todo | Phase 2+ | |
| BL-FE-02 | shadcn/ui + app shell per ui-specs | Todo | Phase 2+ | Spec locked Phase 0 |
| BL-FE-03 | Chat UI + citations rendering | Todo | Phase 3 | |
| BL-FE-04 | Admin document management UI | Todo | Phase 2–3 | |
| BL-FE-05 | History + settings screens | Todo | Phase 3–4 | |
| BL-FE-06 | Analytics dashboard UI | Todo | Phase 6 | |
| BL-FE-07 | A11y pass on primary flows | Todo | Phase 3+ | |
| BL-FE-08 | Multimodal table/image rendering | Todo | Phase 3–4 | P1 · US-MM-02 |
| BL-FE-09 | Domain-denied login state | Todo | Phase 2 | |

## Open decisions (need ADR soon)

| ID | Decision | Status | Target ADR |
|----|----------|--------|------------|
| BL-DEC-01 | Firestore vs Cloud SQL for metadata | Todo | ADR-0006 |
| BL-DEC-02 | Exact embedding model + dimensions | Todo | ADR-0007 |
| BL-DEC-03 | Vector Search index topology / filter schema | Todo | ADR-0007 |
| BL-DEC-04 | STT/TTS provider selection | Deferred | Phase 5 ADR |
| BL-DEC-05 | Ingest enqueue: Cloud Tasks vs Pub/Sub | Todo | Phase 2 ADR |
| BL-DEC-06 | Semantic cache backing store | Todo | Phase 3 |

**Resolved in Phase 0–1:** LangGraph; Vertex AI Vector Search; Cloud Run service split; zero JSON keys + WIF; audience allowlist; CMEK secrets/docs; CI deploy path.

---

## Recently completed

- **2026-07-17** — **Phase 1 complete:** retrospective + engineering report; all Phase 1 foundation items Done (PRs #3–#9).
- **2026-07-17** — **Phase 1.7:** GHA CI + WIF deploy; Artifact Registry `rag-containers`; API Dockerfile; deploy to `rag-api` on main.
- **2026-07-17** — **Phase 1.6:** Cloud Run stubs; OAuth allowlist + Binary Auth tracking.
- **2026-07-17** — **Phase 1.5:** Health endpoints; removed project `storage.admin` from sa-rag-ci.
- **2026-07-17** — **Phase 1.4:** `rag-docs-*` with CMEK and bucket IAM.
- **2026-07-17** — **Phase 1.3:** CMEK keyring + Secret Manager shells.
- **2026-07-17** — **Phase 1.2:** SAs + WIF.
- **2026-07-17** — **Phase 1.1:** Multi-env Terraform + APIs + state buckets.
