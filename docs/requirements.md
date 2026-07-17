# Enterprise RAG Platform — Requirements

**Project:** enterprise-rag-platform  
**GCP project:** set via Terraform `var.gcp_project_id` / env `GCP_PROJECT_ID` (never hard-coded in application code)  
**Current dev example:** `enterprise-rag-platform-502711` (number `642114828076`)  

**Document version:** 3.0 (Phase 0 Gamma — requirements lock)  
**Date:** 2026-07-16  
**Status:** Requirements locked for Phase 1 kickoff (docs complete; implementation follows)

---

## Table of contents

1. [Product vision](#1-product-vision)
2. [Audience & data sources](#2-audience--data-sources)
3. [Personas & roles](#3-personas--roles)
4. [User stories by persona](#4-user-stories-by-persona)
5. [Cross-cutting capability stories](#5-cross-cutting-capability-stories)
6. [Non-functional requirements](#6-non-functional-requirements)
7. [Data & privacy requirements](#7-data--privacy-requirements)
8. [Out of scope](#8-out-of-scope)
9. [Success criteria](#9-success-criteria-platform-mvp)
10. [Traceability](#10-traceability)
11. [Glossary](#11-glossary)

---

## 1. Product vision

A production-grade, GCP-native **Enterprise RAG** platform that lets authenticated users ask natural-language and **voice** questions over **versioned** enterprise documents and receive **grounded** answers with **citations**, **guardrails**, **multimodal** evidence (tables/images where extracted), optional **5-star feedback**, and **privacy-safe analytics**.

### 1.1 Product pillars

| Pillar | User-visible outcome |
|--------|----------------------|
| **Grounded answers** | Answers cite sources; refuse when evidence is weak |
| **Version integrity** | Every citation maps to a published document version |
| **Safe by default** | Injection resistance, ACL at retrieval, no PII in logs/analytics; **zero JSON SA keys** |
| **Installable UX** | PWA: chat, history, admin, analytics on mobile and desktop |
| **Performant retrieval** | Hybrid search + **metadata filtering** + optional **semantic cache** |
| **Operable** | Terraform, least-privilege IAM, WIF/OIDC CI, metrics (p50/p95/p99), cost visibility |

### 1.2 Primary user journeys (summary)

1. **Ask** → authenticated chat → LangGraph orchestration → hybrid retrieval (+ metadata filters, cache) → grounded answer + citations (+ tables/images) → optional 5-star feedback  
2. **Publish** → content admin uploads → version → **ingest-worker** async index → publish becomes retrievable  
3. **Govern** → security/operator reviews refusals, latency, access audit  
4. **Measure** → product owner views volume, quality (held-out eval), feedback stars, cost proxies  

UI detail: [ui-specs.md](./ui-specs.md) · Architecture: [architecture/overview.md](./architecture/overview.md)

---

## 2. Audience & data sources

### 2.1 Allowed audience (auth allowlist)

| Domain | Access |
|--------|--------|
| `chandraailabs.com` | Allowed (primary org) |
| `gmail.com` | Allowed (collaborators / demos) |
| All other domains | Denied at sign-in |

Enforcement: OAuth identity email domain check after Google sign-in (configurable list in Secret Manager / config — not hard-coded secrets). See US-AUTH-01 / US-EU-01.

### 2.2 Data sources (current phase)

Until enterprise customer corpora are onboarded, the platform is developed and demoed with:

| Source type | Use |
|-------------|-----|
| **Synthetic** documents | Controlled fixtures for tests, eval, demos |
| **Public open-source** documents | Non-sensitive sample corpora (licenses respected; attribution where required) |

No production customer PII corpora are required for Phase 0–3 development. Production onboarding of private corpora is a later ops/runbook concern.

### 2.3 Locked platform choices (Gamma)

| Choice | Decision |
|--------|----------|
| Orchestration | **LangGraph** (query path graph) |
| Vector index | **Vertex AI Vector Search** (confirmed) |
| Cloud Run services | **`api`**, **`ingest-worker`**, **`web`** |
| Metadata store | **Firestore (Native mode)** — [ADR-0006](./adr/0006-metadata-store-firestore.md) |
| Load balancer + Cloud Armor | **Later** (not Phase 1 blockers) |

---

## 3. Personas & roles

### 3.1 Personas

| Persona | Goals | Pain points we solve |
|---------|-------|----------------------|
| **End User** | Fast, trusted answers at work | Search fails on policy wording; no source links |
| **Content Admin** | Keep corpus current and auditable | “Which PDF was live when we answered?” |
| **Security / Compliance** | Least privilege, audit, privacy | Query logs with PII; uncontrolled LLM output |
| **Platform Operator** | Uptime, latency, cost, deploys | Opaque RAG failures; click-ops drift |
| **Product Owner** | Adoption and answer quality | No held-out eval; vanity metrics only |
| **Developer / Platform Engineer** | Ship safely with clear contracts | Undocumented APIs; missing ADRs |

### 3.2 Application roles (RBAC)

| Role | Capabilities (summary) |
|------|------------------------|
| `user` | Chat, history (own), voice (when enabled), view citations within ACL |
| `content_admin` | Upload, version, publish/retire docs; view ingest job status |
| `operator` | Metrics dashboards, re-index, config flags (non-secret), health ops |
| `security_auditor` (optional) | Read-only audit & analytics (no content mutation) |
| `admin` | Role assignment; break-glass settings (later phase) |

Roles are least-privilege; elevation is explicit and audited.

---

## 4. User stories by persona

Priority: **P0** = MVP · **P1** = post-MVP near-term · **P2** = later  
Acceptance criteria use Given/When/Then where useful.

---

### 4.1 End User

#### US-EU-01 — Sign in (P0, Phase 1)

**Story:** As an **End User**, I can sign in with Google OAuth so only authorized people use the system.

**Acceptance criteria:**
- Given I am unauthenticated, when I open a protected route, then I am redirected to login.
- Given an identity with email domain `chandraailabs.com` or `gmail.com`, when I complete OAuth, then I land on Chat with my display name.
- Given an identity with any other email domain, when OAuth completes, then access is **denied** with a clear message (no partial session).
- Given session expiry, when I submit a query, then I am prompted to re-auth without losing local draft text when possible.

**Related:** US-AUTH-01 · §2.1 Audience

---

#### US-EU-02 — Ask a grounded question (P0, Phase 3)

**Story:** As an **End User**, I can ask a natural-language question and receive a grounded answer.

**Acceptance criteria:**
- Given a published corpus, when I submit a question, then I receive an answer within NFR latency targets (or a clear timeout error).
- Given supporting chunks exist, when the answer is shown, then at least one citation is attached (doc title, version, locator).
- Given empty or low-confidence retrieval, when generation would be ungrounded, then I see a refusal / insufficient-evidence message (not a free-form guess).

**Related:** US-QA-01, US-QA-03 · [ADR-0004 Guardrails](./adr/0004-guardrails-architecture.md)

---

#### US-EU-03 — Citations & version transparency (P0, Phase 3)

**Story:** As an **End User**, I can see **which document version** supported each answer and open/copy citation details.

**Acceptance criteria:**
- Each citation shows: document title, version id/label, chunk/section locator (page or heading when available).
- I can copy the full answer and citation list.
- I never see citations for documents outside my ACL.

**Related:** US-QA-02, US-DOC-04, US-PWA-03 · [ADR-0003 Versioning](./adr/0003-document-versioning.md)

---

#### US-EU-04 — Conversation history (P1, Phase 4)

**Story:** As an **End User**, I can view my past conversations and continue a thread.

**Acceptance criteria:**
- History lists my sessions only (tenant/user scoped).
- Opening a session restores prior turns for multi-turn context per product rules.
- Delete/archive of a session is available (P1) without deleting operator analytics aggregates.

**Related:** US-QA-04

---

#### US-EU-05 — Collection filter (P1, Phase 4)

**Story:** As an **End User**, I can scope questions to a document collection or set I can access.

**Acceptance criteria:**
- Filter control lists only collections in my ACL.
- Retrieval and generation respect the selected scope.

**Related:** US-QA-05

---

#### US-EU-06 — Voice ask & hear (P1, Phase 5)

**Story:** As an **End User**, I can speak a question and optionally hear the answer in the PWA.

**Acceptance criteria:**
- Mic control starts/stops capture; partial transcript visible when STT supports streaming.
- Cancel returns to text mode without submitting.
- TTS is optional; mute persists per device preference.
- Errors for mic permission / unsupported browser are explicit.

**Related:** US-VOICE-01, US-VOICE-02 · [ui-specs.md § Voice](./ui-specs.md#6-voice-integration)

---

#### US-EU-07 — Install as PWA (P1, Phase 5)

**Story:** As an **End User**, I can install the app on mobile/desktop and open a usable shell offline.

**Acceptance criteria:**
- Install prompt / instructions work on supported browsers.
- Offline: shell + last cached chrome load; online-only actions show offline banner.
- Answers are not fabricated offline from empty cache.

**Related:** US-PWA-01, US-PWA-02

---

#### US-EU-08 — Rate answer quality (5-star) (P0, Phase 3)

**Story:** As an **End User**, I can rate an assistant answer with a **1–5 star** score so product quality can improve.

**Acceptance criteria:**
- Every successful assistant answer (not necessarily refusals) shows a **5-star** control under the message ([ui-specs.md](./ui-specs.md)).
- Feedback is **optional** and **non-blocking** — not submitting stars never blocks chat.
- Submitting or changing a rating persists with message/session id; duplicate submits update (idempotent).
- Analytics store rating + hashed subject + message id + timestamps — **not** full answer text by default.
- Keyboard and screen-reader accessible (named radiogroup / buttons).

**Related:** US-QA-06 · US-PO-04

---

#### US-EU-09 — See tables and images in answers (P1, Phase 3–4)

**Story:** As an **End User**, when evidence includes tables or figures extracted from documents, I can see them rendered in the answer or citation detail.

**Acceptance criteria:**
- Markdown tables in assistant content render as accessible HTML tables.
- Referenced images (from multimodal extraction) render with alt text / caption when available; lazy-load; fail soft if asset missing.
- Images are served only if the user has ACL to the source document version.
- Refusals do not invent images/tables.

**Related:** US-MM-01, US-MM-02 · [ui-specs.md § Multimodal](./ui-specs.md#14-multimodal-rendering)

---

### 4.2 Content Admin

#### US-CA-01 — Upload documents (P0, Phase 2)

**Story:** As a **Content Admin**, I can upload PDF, DOCX, Markdown, and HTML source files.

**Acceptance criteria:**
- Supported MIME types accepted; unsupported types rejected with clear error.
- Upload stores object in CMEK-backed GCS under a version-bound path.
- Virus/size limits enforced (configured max size; default documented in runbook).

**Related:** US-DOC-01

---

#### US-CA-02 — Version & publish (P0, Phase 2)

**Story:** As a **Content Admin**, I can create a new **version** of a document and **publish** it without deleting history.

**Acceptance criteria:**
- Draft → processing → ready → published state machine is visible in Admin UI.
- Publish is blocked until index job succeeds (or explicit “publish when ready” with status).
- Previous published versions remain in history; only active set is retrievable by default.

**Related:** US-DOC-02 · [ADR-0003](./adr/0003-document-versioning.md)

---

#### US-CA-03 — Retire / unpublish (P0, Phase 2)

**Story:** As a **Content Admin**, I can retire or unpublish a version so it is no longer retrieved.

**Acceptance criteria:**
- Retired versions are excluded from retrieval within a bounded propagation window (document in NFR).
- History still shows retired versions for audit.
- Action is audit-logged (actor hashed/id, action, doc/version ids — no file body).

**Related:** US-DOC-03

---

#### US-CA-04 — Ingest job visibility (P0, Phase 2)

**Story:** As a **Content Admin**, I can see parse/chunk/embed job status and failures.

**Acceptance criteria:**
- Job list shows status, timestamps, error summary (no raw secret material).
- Failed jobs can be retried without duplicating published active versions incorrectly (idempotent).

---

#### US-CA-05 — Collection management (P1, Phase 4)

**Story:** As a **Content Admin**, I can group documents into collections and set default ACL labels.

**Acceptance criteria:**
- CRUD for collections (name, description, membership).
- ACL labels documented and enforced at retrieval (see US-GRD-03).

---

#### US-CA-06 — Multimodal extraction on ingest (P1, Phase 2–3)

**Story:** As a **Content Admin**, when I publish documents containing tables and images, the pipeline extracts them for retrieval and citation.

**Acceptance criteria:**
- Ingest detects tables (structure → text/HTML representation) and images (asset + caption/OCR text where configured).
- Extracted assets stored under version-bound GCS paths (CMEK).
- Job status surfaces extraction warnings without failing entire doc unless configured hard-fail.
- Synthetic and open-source fixtures cover at least one table-heavy and one image-containing sample.

**Related:** US-MM-01

---

### 4.3 Security / Compliance Officer

#### US-SC-01 — PII-safe logs & analytics (P0, Phase 1+)

**Story:** As a **Security Officer**, I require hashed user identifiers and no raw query text in default analytics.

**Acceptance criteria:**
- Application logs use structured JSON; user id is hashed (or equivalent irreversible token).
- BigQuery analytics tables store metadata only by default (latency, status, token counts, collection ids).
- Spot-check runbook exists to verify absence of raw PII fields.

**Related:** US-GRD-02, US-ANL-04, NFR-PRV-01

---

#### US-SC-02 — Prompt injection & jailbreak resistance (P0, Phase 3–4)

**Story:** As a **Security Officer**, I require prompt-injection and jailbreak attempts to be blocked or neutralized.

**Acceptance criteria:**
- Document content is treated as untrusted data in prompts (not instructions).
- Known injection patterns and “ignore previous instructions” attempts do not elevate privileges or dump secrets.
- Violations can be counted in metrics without storing full attack text by default (optional quarantine store later).

**Related:** US-GRD-01 · [ADR-0004](./adr/0004-guardrails-architecture.md)

---

#### US-SC-03 — ACL at retrieval (P0, Phase 3)

**Story:** As a **Security Officer**, users never receive answers citing documents they cannot access.

**Acceptance criteria:**
- Retrieval filters by ACL before fusion/generation.
- Post-generation citation filter as defense-in-depth.
- Automated test: user A cannot retrieve user B’s restricted collection.

**Related:** US-GRD-03

---

#### US-SC-04 — Admin action audit (P1, Phase 2)

**Story:** As a **Security Officer**, I can review audit logs of admin actions without free-text PII fields.

**Acceptance criteria:**
- Events: login, role change, publish, retire, re-index, config change.
- Fields: timestamp, actor hash, action, resource ids, correlation id.
- Retention policy documented.

**Related:** US-AUTH-03

---

### 4.4 Platform Operator

#### US-OP-01 — Deploy via pipeline (P0, Phase 1–2)

**Story:** As a **Platform Operator**, I can deploy **api**, **ingest-worker**, and **web** Cloud Run services via automated pipelines.

**Acceptance criteria:**
- CI builds from pinned deps; smoke test hits live service `status.url` (never revision traffic URL alone as canonical).
- Three services deployable independently with documented images.
- **Zero JSON service-account key files** in CI or runtime; **Workload Identity Federation (WIF)** / OIDC only ([ADR-0005](./adr/0005-security-posture.md)).
- Rollback path documented.

**Related:** US-OPS-01, US-OPS-04

---

#### US-OP-02 — Terraform-managed infra (P0, Phase 0–1)

**Story:** As a **Platform Operator**, all infrastructure is defined in Terraform and is idempotent.

**Acceptance criteria:**
- `terraform plan` is the source of truth for drift review.
- Project/region via variables (`var.gcp_project_id`, region var); no hard-coded real project IDs in repo.
- Re-apply is safe (idempotent resources).

**Related:** US-OPS-02

---

#### US-OP-03 — Secrets hygiene (P0, continuous)

**Story:** As a **Platform Operator**, secrets never appear in git or committed container env files.

**Acceptance criteria:**
- `.env` gitignored; `.env.example` placeholders only.
- Secret Manager for deploy-time secrets.
- detect-secrets (or equivalent) in CI when CI lands.

**Related:** US-OPS-03, NFR-SEC-02

---

#### US-OP-04 — Latency & error dashboards (P0 basic / P1 full)

**Story:** As a **Platform Operator**, I can view p50/p95/p99 latency and error rates.

**Acceptance criteria:**
- Metrics exported for query path stages (retrieve, generate, total).
- Alert hooks defined for critical thresholds (wired in ops phase).

**Related:** US-ANL-02, NFR-OBS-03

---

#### US-OP-05 — Re-index after pipeline fix (P1, Phase 2–3)

**Story:** As a **Platform Operator**, I can re-index a document version after pipeline fixes.

**Acceptance criteria:**
- Re-index does not corrupt active alias until job succeeds (atomic swap).
- Job is auditable and rate-limited to protect cost (NFR-COST-03).

**Related:** US-DOC-05, BL-ING-06

---

#### US-OP-06 — Guardrail / safety config (P1, Phase 4)

**Story:** As a **Platform Operator**, I can tune refusal thresholds and safety policies via config (not code deploy for every knob).

**Acceptance criteria:**
- Config in Secret Manager or remote config store with versioning.
- Changes audit-logged; invalid config fails closed.

**Related:** US-GRD-04

---

#### US-OP-07 — Health endpoints with version metadata (P0, Phase 1)

**Story:** As a **Platform Operator**, I can call `/health` and `/ready` and see **version** and **deployed_at** for smoke tests and incident triage.

**Acceptance criteria:**
- Both endpoints return JSON including at least: `status`, `service`, `version`, `deployed_at` (ISO-8601 UTC build/deploy timestamp).
- `/ready` may include dependency readiness flags without leaking secrets.
- Values come from build/deploy env (e.g. git SHA / image tag + deploy time) — not hand-edited per request.
- Smoke tests assert presence of `version` and `deployed_at`.

**Related:** NFR-REL-03, NFR-OBS-06

---

### 4.5 Product Owner

#### US-PO-01 — Usage analytics (P1, Phase 6)

**Story:** As a **Product Owner**, I can view query volume, latency percentiles, and refusal rates.

**Acceptance criteria:**
- Dashboard filters by date range and environment.
- No raw query text by default.
- Export of aggregates allowed (CSV) without user-level PII.

**Related:** US-ANL-01

---

#### US-PO-02 — Quality on held-out set (P1, Phase 6)

**Story:** As a **Product Owner**, I can track answer quality on a **held-out** evaluation set.

**Acceptance criteria:**
- Eval set is not used for prompt “training” contamination or threshold fishing without documentation.
- Metrics: relevancy / citation accuracy (definitions in eval runbook).
- CI quality gate uses held-out only (protocol non-negotiable).

**Related:** US-ANL-03

---

#### US-PO-03 — Cost visibility (P1, Phase 6)

**Story:** As a **Product Owner**, I can see token/embedding cost proxies over time.

**Acceptance criteria:**
- Daily/weekly token estimates by model id.
- Spike detection relative to baseline (alert optional).

**Related:** NFR-COST-02

---

#### US-PO-04 — View feedback aggregates (P1, Phase 6)

**Story:** As a **Product Owner**, I can view aggregate 5-star feedback distributions over time (not raw PII).

**Acceptance criteria:**
- Dashboard shows mean stars, histogram 1–5, volume of rated vs unrated answers.
- No user email or raw answer text in the default analytics view.
- Filter by date range / environment.

**Related:** US-EU-08, US-QA-06, US-ANL-05

---

### 4.6 Developer / Platform Engineer

#### US-DEV-01 — Local run (P0, Phase 0+)

**Story:** As a **Developer**, I can run API and UI locally with documented steps and health checks.

**Acceptance criteria:**
- README + component READMEs work on Python 3.12 and Node 22.
- `/health` and `/ready` return success for smoke tests.

---

#### US-DEV-02 — OpenAPI contract (P0, Phase 1+)

**Story:** As a **Developer**, I can discover API contracts via OpenAPI for frontend integration.

**Acceptance criteria:**
- FastAPI generates OpenAPI at `/docs` / `/openapi.json`.
- Breaking changes require version note in CHANGELOG.

---

#### US-DEV-03 — ADRs & backlog discipline (P0, continuous)

**Story:** As a **Developer**, significant decisions are in ADRs and deferrals are in `docs/backlog.md`.

**Acceptance criteria:**
- New architectural choices produce or update an ADR.
- Deferred work is not chat-only.

**Related:** NFR-MNT-01, NFR-MNT-02

---

#### US-DEV-04 — LangGraph orchestration boundary (P0, Phase 3)

**Story:** As a **Developer**, query orchestration (retrieve → ground → generate → guard) is implemented as an explicit **LangGraph** graph with testable nodes.

**Acceptance criteria:**
- Graph nodes and edges documented in architecture overview.
- Unit tests can invoke nodes without full HTTP stack.
- Graph config does not embed secrets.

**Related:** ADR-0002 · architecture overview

---

## 5. Cross-cutting capability stories

Stable IDs retained from Phase 0 Alpha/Beta; **new Gamma IDs appended** (never renumber existing).

| ID | Story (short) | Priority | Phase |
|----|---------------|----------|-------|
| US-AUTH-01 | Google OAuth sign-in; allowlist `chandraailabs.com` + `gmail.com` | P0 | 1 |
| US-AUTH-02 | Role assignment (least privilege) | P0 | 1–2 |
| US-AUTH-03 | Admin audit logs without free-text PII | P1 | 2 |
| US-DOC-01 | Upload PDF/DOCX/MD/HTML | P0 | 2 |
| US-DOC-02 | Publish new version without deleting history | P0 | 2 |
| US-DOC-03 | Retire/unpublish version | P0 | 2 |
| US-DOC-04 | Answer shows document version used | P0 | 3 |
| US-DOC-05 | Re-index document version | P1 | 2–3 |
| US-QA-01 | NL question → grounded answer (LangGraph path) | P0 | 3 |
| US-QA-02 | Citations on answers | P0 | 3 |
| US-QA-03 | Insufficient-evidence refusal | P0 | 3 |
| US-QA-04 | Multi-turn conversation | P1 | 4 |
| US-QA-05 | Filter by collection (metadata filter UX) | P1 | 4 |
| US-QA-06 | 5-star feedback on answers | P0 | 3 |
| US-QA-07 | Semantic caching for repeated/similar queries | P1 | 3–4 |
| US-QA-08 | Server-side metadata filtering for retrieval performance | P0 | 3 |
| US-MM-01 | Extract tables/images at ingest | P1 | 2–3 |
| US-MM-02 | Render tables/images in chat / citation UI | P1 | 3–4 |
| US-VOICE-01 | STT + TTS in PWA | P1 | 5 |
| US-VOICE-02 | Cancel voice → text fallback | P1 | 5 |
| US-VOICE-03 | STT/TTS provider via config | P2 | 5 |
| US-GRD-01 | Injection/jailbreak resistance | P0 | 3–4 |
| US-GRD-02 | PII redaction / hashed IDs in logs | P0 | 1+ |
| US-GRD-03 | ACL-safe citations | P0 | 3 |
| US-GRD-04 | Configurable safety policies | P1 | 4 |
| US-ANL-01 | Volume, latency, refusal dashboards | P1 | 6 |
| US-ANL-02 | p50/p95/p99 + error rates | P0/P1 | 1+/6 |
| US-ANL-03 | Held-out quality metrics | P1 | 6 |
| US-ANL-04 | Analytics without raw PII | P0 | 6 |
| US-ANL-05 | Aggregate star-rating analytics | P1 | 6 |
| US-PWA-01 | Installable PWA | P1 | 5 |
| US-PWA-02 | Offline UI shell | P2 | 5 |
| US-PWA-03 | Copy answer + open citations | P0 | 3 |
| US-OPS-01 | Deploy api + ingest-worker + web (Cloud Run) | P0 | 1–2 |
| US-OPS-02 | Idempotent Terraform | P0 | 0–1 |
| US-OPS-03 | Secrets never in git | P0 | 0+ |
| US-OPS-04 | Zero JSON SA keys; WIF/OIDC only | P0 | 1 |
| US-OPS-05 | `/health` + `/ready` return version + deployed_at | P0 | 1 |

### 5.1 New capability detail (Gamma)

#### US-QA-06 — 5-star feedback (P0, Phase 3)

**Story:** As a product system, each answer can collect a 1–5 star rating from the end user.

**Acceptance:** See US-EU-08. API: `POST /feedback` (or equivalent) with message_id, stars∈[1,5]; optional free-text comment deferred (P2) to avoid PII sprawl.

#### US-QA-07 — Semantic caching (P1, Phase 3–4)

**Story:** As the platform, semantically similar questions within ACL/collection scope can reuse prior retrieval/generation results to cut latency and cost.

**Acceptance criteria:**
- Cache key incorporates: normalized query embedding (or hash of embedding bucket), principal ACL scope, collection filter, **active corpus version fingerprint**.
- Cache **miss** on publish/retire that changes active set for that scope.
- Cached responses still enforce AuthZ on read (no cross-user leakage).
- Metrics: hit/miss ratio, latency for hit vs miss.
- Invalidation strategy documented; TTL + event-driven bust on publish.

#### US-QA-08 — Metadata filtering (performance) (P0, Phase 3)

**Story:** As the platform, retrieval applies **metadata filters** (collection, document ids, version active flag, ACL labels) at the vector/sparse query layer to reduce candidate set and latency.

**Acceptance criteria:**
- Vertex AI Vector Search queries include restrict/filter on metadata fields (exact schema in embed ADR).
- BM25 path also respects the same filter predicates.
- Filters are mandatory for ACL labels (security), optional for UX collection scope (US-QA-05).
- Benchmark note: filtered retrieval must not return out-of-filter chunks (correctness > speed).

---

## 6. Non-functional requirements

> **Measurement rule:** Performance and coverage gates use **measured baselines − buffer**, not aspirational targets. Numbers below are the **confirmed planning envelopes** for Phase 1+ design; re-measure before promoting to hard CI gates.

### 6.1 Performance (confirmed planning envelopes)

| ID | Requirement | Planning envelope | Notes |
|----|-------------|-------------------|-------|
| NFR-PERF-01 | Interactive text Q&A end-to-end latency | **p50 < 3s**, **p95 < 8s** (dev/staging envelope) | Semantic cache hits expected much lower; re-baseline before prod gate (actual − 2%) |
| NFR-PERF-02 | Time-to-first-token (streaming, if enabled) | p50 < 1.5s | Optional Phase 3+ |
| NFR-PERF-03 | Ingestion | Async on **ingest-worker**; must not block query path on **api** | |
| NFR-PERF-04 | Cold start (Cloud Run) | Acceptable in non-prod | min-instances strategy in prod later |
| NFR-PERF-05 | Voice round-trip (STT→answer→TTS) | Track separately; soft target after baseline | Phase 5 |
| NFR-PERF-06 | Admin list pages | p95 < 2s for metadata lists | Pagination required |
| NFR-PERF-07 | Metadata-filtered retrieval | Filters applied at index query time | Correctness over speed (US-QA-08) |
| NFR-PERF-08 | Semantic cache hit latency | Track p50 hit vs miss | P1 feature (US-QA-07) |

### 6.2 Scalability

| ID | Requirement |
|----|-------------|
| NFR-SCALE-01 | Stateless **api** and **web**; horizontal scale on Cloud Run |
| NFR-SCALE-02 | **ingest-worker** scales independently of query path |
| NFR-SCALE-03 | Pagination + cursor on all list APIs |
| NFR-SCALE-04 | Rate limits per user/IP (config) to protect LLM spend |

### 6.3 Reliability & availability

| ID | Requirement |
|----|-------------|
| NFR-REL-01 | Stateless instances; no sticky sessions |
| NFR-REL-02 | Idempotent ingest, publish, re-index, feedback submit |
| NFR-REL-03 | `/health` (liveness) and `/ready` (readiness) on **api** (and workers as applicable) |
| NFR-REL-03a | Health payloads **must** include `version` and `deployed_at` (ISO-8601 UTC) plus `status` / `service` |
| NFR-REL-04 | Graceful degradation: if vector index down, fail closed for ungrounded gen |
| NFR-REL-05 | Publish uses atomic active-version pointer / alias swap after dual-index ready |

### 6.4 Security

| ID | Requirement |
|----|-------------|
| NFR-SEC-01 | Least-privilege **custom service accounts** per Cloud Run service; roles listed in runbooks |
| NFR-SEC-02 | Secrets in Secret Manager only |
| NFR-SEC-03 | CMEK on GCS and other supported data stores from foundation phase |
| NFR-SEC-04 | Non-root container user (uid/gid **1001**) |
| NFR-SEC-05 | No PII in application logs; hash user identifiers |
| NFR-SEC-06 | detect-secrets (or equivalent) in CI when CI is introduced |
| NFR-SEC-07 | HTTPS only at edge; secure cookies / token storage practices |
| NFR-SEC-08 | Dependency pinning; CI installs only from declared lock/requirements files |
| NFR-SEC-09 | AuthZ on every mutating admin endpoint |
| NFR-SEC-10 | **Zero JSON service-account key files** — never create, download, commit, or mount `*.json` SA keys for runtime or CI |
| NFR-SEC-11 | **WIF + OIDC** for CI/CD and keyless GCP auth; human users use ADC / gcloud user creds locally |
| NFR-SEC-12 | **Defence-in-depth**: network (later LB/Armor), identity, AuthZ, guardrails, privacy egress — no single control is sufficient |
| NFR-SEC-13 | Auth email domain allowlist: `chandraailabs.com`, `gmail.com` only (deny all other domains at sign-in) |
| NFR-SEC-14 | **Binary Authorization (future / deferred):** Cloud Run services **SHALL** eventually be protected by Binary Authorization so that only **signed and attested** container images can run. Requires attestors, KMS signing keys, and a Binary Authorization policy. **Not required for Phase 1 stubs.** Tracked as BL-SEC-09 / BL-FND-26. |

See [ADR-0005 Security Posture](./adr/0005-security-posture.md) · [OAuth allowlist runbook](./runbooks/oauth-domain-allowlist.md).

### 6.5 Privacy & compliance

| ID | Requirement |
|----|-------------|
| NFR-PRV-01 | Analytics: hashed user IDs + metadata only (no raw query by default) |
| NFR-PRV-02 | Document ACL enforced at retrieval time |
| NFR-PRV-03 | Design for **DPDP Act 2023** (India); data residency documented in ADRs |
| NFR-PRV-04 | Data retention windows documented for logs, audit, conversations, feedback |
| NFR-PRV-05 | Right-to-erasure path for user conversation data (process + API later) |
| NFR-PRV-06 | Star ratings stored without raw answer body by default |

### 6.6 Observability

| ID | Requirement |
|----|-------------|
| NFR-OBS-01 | Structured JSON logging (Cloud Logging compatible) |
| NFR-OBS-02 | Correlation IDs across LangGraph nodes → respond |
| NFR-OBS-03 | Metrics: latency percentiles, error rate, token usage, retrieval hit rate, refusal rate, **cache hit rate**, **feedback stars** |
| NFR-OBS-04 | Alert policies for critical thresholds (ops phase) |
| NFR-OBS-05 | Per-query analytics row to BigQuery: metadata only |
| NFR-OBS-06 | Deploy identity: `version` + `deployed_at` on health endpoints for smoke/incident correlation |

### 6.7 Maintainability & process

| ID | Requirement |
|----|-------------|
| NFR-MNT-01 | ADRs for every significant architecture decision |
| NFR-MNT-02 | Living `docs/backlog.md`; `CHANGELOG.md` per PR set |
| NFR-MNT-03 | Pinned dependencies; hermetic CI installs |
| NFR-MNT-04 | Three-Agent Protocol for design/build/verify |
| NFR-MNT-05 | UI follows [ui-specs.md](./ui-specs.md); design system **shadcn/ui** |
| NFR-MNT-06 | Issues logged in `docs/issues_log.md` with root cause |
| NFR-MNT-07 | Query orchestration via **LangGraph** (ADR-0002) |

### 6.8 Accessibility & UX quality

| ID | Requirement |
|----|-------------|
| NFR-A11Y-01 | WCAG 2.2 **AA** target for primary flows (chat, login, admin critical paths) |
| NFR-A11Y-02 | Keyboard operable chat compose, star rating, and primary nav |
| NFR-A11Y-03 | Visible focus states; sufficient color contrast |
| NFR-A11Y-04 | Voice controls labeled for screen readers |
| NFR-A11Y-05 | Tables in answers use proper `<table>` semantics; images have alt text |
| NFR-UX-01 | Mobile-first layouts; usable at 360px width |
| NFR-UX-02 | Prefer progressive enhancement for PWA |
| NFR-UX-03 | Feedback UI optional and non-blocking |

### 6.9 Cost

| ID | Requirement |
|----|-------------|
| NFR-COST-01 | Scale-to-zero friendly in non-prod |
| NFR-COST-02 | Token/embedding cost visibility in analytics phase |
| NFR-COST-03 | No unbounded re-embed loops; budgets/rate limits |
| NFR-COST-04 | Model IDs configurable per env to control spend |
| NFR-COST-05 | Semantic cache used to reduce duplicate Gemini/embed cost where safe |

### 6.10 Quality (RAG)

| ID | Requirement |
|----|-------------|
| NFR-QLT-01 | Held-out evaluation set for quality gates |
| NFR-QLT-02 | Never use test/eval set as training or silent prompt tuning data |
| NFR-QLT-03 | Citation required when answer asserts factual claims from corpus |
| NFR-QLT-04 | Hybrid retrieval (sparse + dense + RRF) as default path ([ADR-0001](./adr/0001-high-level-architecture.md)) |
| NFR-QLT-05 | Dense index = **Vertex AI Vector Search** (locked) |
| NFR-QLT-06 | Multimodal extractions grounded to source version assets |

---

## 7. Data & privacy requirements

| Topic | Rule |
|-------|------|
| Document binaries | GCS + CMEK; versioned object keys |
| Multimodal assets | Tables/images under version-bound keys; ACL with parent doc |
| Chunk metadata | Store version id, ACL labels, locators, modality flags |
| Conversations | User-scoped; retention policy TBD in runbook |
| Feedback | Stars + message id + subject hash; no answer body by default |
| Analytics | Hashed subject id; latency; status; model; tokens; collection ids; cache hit; stars |
| Logs | No raw document text at INFO; DEBUG local-only |
| Dev corpora | Synthetic + public open-source only until private onboarding |
| Cross-border | Prefer primary region from Terraform `var.region`; document any exception in ADR |
| Credentials | **No JSON SA keys** anywhere in the delivery path |

---

## 8. Out of scope

### Near-term (Phase 0–1)
- Multi-region active-active  
- Native iOS/Android apps (PWA first)  
- Multi-tenant SaaS billing  
- On-prem deployment  
- Fine-tuning custom LLMs  
- **Global HTTPS LB + Cloud Armor** (scheduled later)  
- Metadata store technology lock (ADR pending)

### Explicit non-goals (until reopened via ADR)
- Guaranteeing 100% factual correctness of LLM phrasing (we guarantee grounding policy + citations)  
- Real-time collaborative editing of source documents  
- Full e-discovery legal hold suite  
- Free-text feedback comments in MVP (stars only; comments P2)

---

## 9. Success criteria (Platform MVP)

1. Authenticated allowlisted **user** can ask a question and receive a **cited** answer from a **published** version.  
2. **Content admin** can upload → version → publish → retire with audit trail (ingest-worker).  
3. Guardrails **refuse** ungrounded answers under empty/low-confidence retrieval.  
4. Analytics path stores **no raw PII** by default; optional **5-star** feedback works non-blocking.  
5. Core infra is **Terraform-managed** and redeployable (`var.gcp_project_id`); **zero JSON SA keys**.  
6. Held-out **eval set** exists for quality gates (synthetic/OSS fixtures acceptable initially).  
7. `/health` and `/ready` expose **version** + **deployed_at**.  
8. PWA shell meets mobile-first + install path (voice can be Phase 5 stretch relative to text MVP).

---

## 10. Traceability

| Artifact | Path |
|----------|------|
| UI / UX specification | [docs/ui-specs.md](./ui-specs.md) |
| Architecture overview | [docs/architecture/overview.md](./architecture/overview.md) |
| ADR-0001 Architecture | [docs/adr/0001-high-level-architecture.md](./adr/0001-high-level-architecture.md) |
| ADR-0002 Tech stack | [docs/adr/0002-tech-stack.md](./adr/0002-tech-stack.md) |
| ADR-0003 Document versioning | [docs/adr/0003-document-versioning.md](./adr/0003-document-versioning.md) |
| ADR-0004 Guardrails | [docs/adr/0004-guardrails-architecture.md](./adr/0004-guardrails-architecture.md) |
| ADR-0005 Security posture | [docs/adr/0005-security-posture.md](./adr/0005-security-posture.md) |
| Living backlog | [docs/backlog.md](./backlog.md) |
| Engineering protocol | [docs/grok-three-agent-protocol.md](./grok-three-agent-protocol.md) |

---

## 11. Glossary

| Term | Meaning |
|------|---------|
| **Chunk** | Indexed fragment of a document version used for retrieval |
| **Citation** | User-visible pointer to source chunk (title, version, locator) |
| **Collection** | Logical group of documents for scope and ACL |
| **Grounded answer** | Generation constrained to retrieved evidence |
| **Hybrid retrieval** | Sparse (BM25) + dense (vector) search combined (RRF) |
| **LangGraph** | Graph-based orchestration library for the query pipeline |
| **Metadata filter** | Restricts retrieval candidates by structured fields (ACL, collection, version) |
| **Multimodal** | Tables/images extracted from docs and usable in retrieval/UI |
| **Publish** | Make a version active for retrieval |
| **RRF** | Reciprocal Rank Fusion |
| **Refusal** | Safe response when evidence is insufficient or policy blocks |
| **Semantic cache** | Reuse of prior answers/retrieval for similar queries within scope |
| **Version** | Immutable snapshot of a document’s content for audit and retrieval |
| **WIF** | Workload Identity Federation (keyless CI → GCP) |
