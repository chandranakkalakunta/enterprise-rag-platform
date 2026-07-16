# Architecture Overview — Enterprise RAG Platform

**Version:** 1.0 (Phase 0 Beta)  
**Date:** 2026-07-16  
**Status:** Pre-implementation refinement  

Governing ADRs: [0001](../adr/0001-high-level-architecture.md) · [0002](../adr/0002-tech-stack.md) · [0003](../adr/0003-document-versioning.md) · [0004](../adr/0004-guardrails-architecture.md)

---

## 1. Purpose

This document expands ADR-0001 into an implementable **component breakdown**, data/control flows, and diagram set for engineering phases. It does not replace ADRs for decision history.

**GCP project/region:** always from Terraform/config (`var.gcp_project_id`, `var.region`) — never hard-coded real project IDs in application code.

---

## 2. Context diagram

```text
                 ┌──────────────────────┐
                 │  Identity Provider   │
                 │  (Google OAuth)      │
                 └──────────┬───────────┘
                            │
┌───────────────┐    HTTPS  │   ┌─────────────────────────────────────┐
│  End users    │───────────┼──▶│  Next.js PWA (Cloud Run)            │
│  Admins       │           │   │  Chat · Admin · Analytics · Voice UI│
└───────────────┘           │   └──────────────────┬──────────────────┘
                            │                      │ JWT / session
                            │                      ▼
                            │   ┌─────────────────────────────────────┐
                            └──▶│  FastAPI API (Cloud Run)              │
                                │  AuthZ · Guardrails · Orchestration │
                                └───────┬───────────┬─────────┬───────┘
                    ┌───────────────────┼───────────┼─────────┼───────────────────┐
                    ▼                   ▼           ▼         ▼                   ▼
             ┌────────────┐    ┌────────────┐ ┌─────────┐ ┌──────────┐   ┌────────────┐
             │ Ingestion  │    │ Retrieval  │ │Generate │ │ Analytics│   │  Secrets   │
             │ workers    │    │ hybrid+RRF │ │ Gemini  │ │ BigQuery │   │  Manager   │
             └─────┬──────┘    └─────┬──────┘ └────┬────┘ └────┬─────┘   └────────────┘
                   ▼                 ▼              ▼           ▼
             ┌──────────┐    ┌────────────┐  ┌──────────┐ ┌──────────┐
             │ GCS CMEK │    │ BM25 store │  │ Vertex   │ │ Logging/ │
             │ + meta   │    │ + Vector   │  │ AI       │ │ Monitor  │
             └──────────┘    └────────────┘  └──────────┘ └──────────┘
```

---

## 3. Logical component breakdown

### 3.1 Frontend (`frontend/`)

| Component | Responsibility |
|-----------|----------------|
| **App shell** | Nav, auth gate, offline banner, role-based routes |
| **Chat module** | Composer, messages, citations, streaming UX |
| **History module** | Session list/detail |
| **Admin module** | Upload, versions, jobs |
| **Analytics module** | KPI cards, charts (metadata only) |
| **Voice module** | Mic/TTS controls; feature-flagged |
| **PWA layer** | Manifest, service worker, install affordances |
| **Design system** | shadcn/ui + domain components ([ui-specs.md](../ui-specs.md)) |

### 3.2 Backend API (`backend/app/`)

| Package / area | Responsibility |
|----------------|----------------|
| `api/` | HTTP routes: auth, chat, docs, jobs, analytics, voice |
| `core/` | Settings, logging, security middleware, correlation IDs |
| `services/retrieval/` | BM25 + dense + RRF, ACL filters |
| `services/generation/` | Prompt assembly, Gemini calls, citation packaging |
| `services/ingestion/` | Parse, chunk, embed, index writers |
| `services/versioning/` | Version state machine, publish/retire, alias swap |
| `services/guardrails/` | Input/output checks, refusal policy ([ADR-0004](../adr/0004-guardrails-architecture.md)) |
| `services/analytics/` | Emit metadata events to BigQuery |
| `models/` | Pydantic schemas / domain types |

### 3.3 Async workers

Prefer **Cloud Tasks / Cloud Run jobs** (decision refine Phase 2) for:

- parse → chunk → embed → index  
- re-index  
- bulk retire propagation  

Query path **must not** wait on heavy ingest.

### 3.4 Data stores

| Store | Data | Notes |
|-------|------|-------|
| **GCS (CMEK)** | Raw files per version | Immutable object per version id |
| **Metadata DB** | Docs, versions, ACL, jobs, sessions | Firestore vs SQL → future ADR if not decided by Phase 2 |
| **Sparse index** | BM25 corpus per active set | Rebuild/swap on publish |
| **Dense index** | Embeddings in Vertex Vector Search | Version-aware filters/namespaces |
| **BigQuery** | Analytics facts | Hashed subject; no raw query default |
| **Secret Manager** | OAuth, API keys, model config secrets | — |

### 3.5 Cross-cutting

| Concern | Implementation sketch |
|---------|----------------------|
| AuthN | Google OAuth → JWT/session validation on API |
| AuthZ | RBAC + document ACL labels at retrieval |
| Observability | JSON logs, metrics, correlation id |
| Config | Env + Secret Manager; model IDs pinned per env |
| IaC | Terraform modules under `terraform/` |

---

## 4. Query path (control flow)

```text
Client                 API                  Guardrails         Retrieval           Generation           Analytics
  |                     |                       |                  |                    |                    |
  |-- POST /query ----->|                       |                  |                    |                    |
  |                     |-- validate authz ---->|                  |                    |                    |
  |                     |-- input checks ------>|                  |                    |                    |
  |                     |                       |-- ACL+query ---->|                    |                    |
  |                     |                       |                  |-- hybrid+RRF ----->|                    |
  |                     |                       |                  |<-- chunks ---------|                    |
  |                     |                       |-- ground policy -|                    |                    |
  |                     |                       |  (refuse?)       |                    |                    |
  |                     |                       |----------------->|-- prompt+cite ---->|                    |
  |                     |                       |                  |                    |-- Gemini --------->|
  |                     |                       |-- output check --|                    |                    |
  |                     |<----- answer+citations+meta -------------|                    |                    |
  |                     |-- emit metadata --------------------------------------------------------------->|
  |<-- 200 JSON --------|                       |                  |                    |                    |
```

**Failure modes:**

| Condition | Behavior |
|-----------|----------|
| No chunks / low confidence | Refusal (US-QA-03); no free hallucination |
| Vector index error | Fail closed for generation if no safe sparse-only policy enabled |
| Unauthorized collection | Empty retrieval for that scope; no leakage |
| Upstream Gemini timeout | 504/408 with correlation id; client retry guidance |

---

## 5. Ingestion & versioning path

See [ADR-0003](../adr/0003-document-versioning.md).

```text
Upload → Object (GCS) → Version=DRAFT
       → Job: parse → chunk → embed → write indexes (staging)
       → Version=READY
       → Publish → atomic activate (alias/pointer) → Version=PUBLISHED (active)
       → Retire → remove from active retrieval → Version=RETIRED (history kept)
```

---

## 6. Guardrails placement

See [ADR-0004](../adr/0004-guardrails-architecture.md).

```text
[Client input]
    → AuthZ
    → Input guard (injection heuristics, size limits, rate limit)
    → Retrieval (ACL filter)
    → Grounding gate (enough evidence?)
    → Generation (data vs instructions separation)
    → Output guard (citation consistency, sensitive pattern redaction in logs)
    → Response
```

---

## 7. Analytics path (privacy-safe)

```text
Query completed
  → Build event {
        event_id, ts, env,
        subject_hash,          # not raw email
        status,                # ok | refusal | error
        latency_ms_total,
        latency_ms_retrieve,
        latency_ms_generate,
        model_id,
        token_in, token_out,
        collection_ids[],      # if applicable
        refusal_code?,
        correlation_id
     }
  → BigQuery (batch or streaming insert)
  → Dashboards (UI / Looker later)
```

**Not stored by default:** raw question text, raw answer text, document body.

---

## 8. Deployment view (target)

```text
                    ┌─────────────────────┐
                    │ Cloud Build + WIF   │
                    └──────────┬──────────┘
                               │ images
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
   Artifact Registry    Cloud Run (API)     Cloud Run (Web)
          │                    │                    │
          └────────────┬───────┴────────┬───────────┘
                       ▼                ▼
                 Secret Manager    Cloud Monitoring
                       │
                       ▼
                 Vertex AI · GCS · BQ · Vector Search
```

Environments: `dev` → `staging` → `prod` via Terraform env dirs/workspaces; each supplies its own `gcp_project_id` through tfvars (not committed secrets).

---

## 9. Repository mapping

| Path | Architecture slice |
|------|--------------------|
| `frontend/` | PWA + UI modules |
| `backend/app/api` | Edge HTTP |
| `backend/app/services/*` | Domain services |
| `terraform/` | GCP resources |
| `docs/adr/` | Decisions |
| `docs/ui-specs.md` | UX contract |
| `docs/requirements.md` | Product contract |

---

## 10. Open decisions (tracked)

| Topic | Tracking | Target |
|-------|----------|--------|
| Firestore vs Cloud SQL for metadata | backlog BL-DEC-01 | ADR-0005 (or before Phase 2) |
| Exact embedding model + dimensions | BL-DEC-02 | ADR before Phase 2–3 |
| Vector Search index topology | BL-DEC-03 | with embeddings ADR |
| STT/TTS provider | BL-DEC-04 | Phase 5 ADR |
| Streaming tokens to client | backlog | Phase 3 design note |

---

## 11. Related documents

- [requirements.md](../requirements.md)  
- [ui-specs.md](../ui-specs.md)  
- [backlog.md](../backlog.md)  
- [grok-three-agent-protocol.md](../grok-three-agent-protocol.md)  
