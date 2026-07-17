# Architecture Overview — Enterprise RAG Platform

**Version:** 1.1 (Phase 0 Gamma)  
**Date:** 2026-07-16  
**Status:** Requirements-locked pre-implementation view  

Governing ADRs: [0001](../adr/0001-high-level-architecture.md) · [0002](../adr/0002-tech-stack.md) · [0003](../adr/0003-document-versioning.md) · [0004](../adr/0004-guardrails-architecture.md) · [0005](../adr/0005-security-posture.md) · [0006](../adr/0006-metadata-store-firestore.md)

---

## 1. Purpose

This document expands ADR-0001 into an implementable **component breakdown**, data/control flows, and diagram set for engineering phases. It does not replace ADRs for decision history.

**GCP project/region:** always from Terraform/config (`var.gcp_project_id`, `var.region`) — never hard-coded in application code.  
**Current dev example project ID:** `enterprise-rag-platform-502711` (number `642114828076`).

**Audience:** OAuth allowlist `chandraailabs.com` + `gmail.com`.  
**Corpora (near term):** synthetic + public open-source documents.

---

## 2. Context diagram (three Cloud Run services)

```text
                 ┌──────────────────────┐
                 │  Identity Provider   │
                 │  (Google OAuth)      │
                 │  allowlist domains   │
                 └──────────┬───────────┘
                            │
┌───────────────┐    HTTPS  │   ┌─────────────────────────────────────┐
│  End users    │───────────┼──▶│  Cloud Run: web (Next.js PWA)       │
│  Admins       │           │   │  Chat · Admin · Analytics · Voice   │
└───────────────┘           │   └──────────────────┬──────────────────┘
                            │                      │ JWT / session
                            │                      ▼
                            │   ┌─────────────────────────────────────┐
                            └──▶│  Cloud Run: api (FastAPI)             │
                                │  AuthZ · LangGraph · Guardrails     │
                                │  Feedback · Semantic cache          │
                                └───┬───────────┬───────────┬─────────┘
                    ┌───────────────┼───────────┼───────────┼──────────────┐
                    ▼               ▼           ▼           ▼              ▼
             ┌────────────┐ ┌────────────┐ ┌────────┐ ┌──────────┐ ┌────────────┐
             │ Cloud Run  │ │ Retrieval  │ │Gemini  │ │ Analytics│ │  Secrets   │
             │ ingest-    │ │ hybrid+RRF │ │Vertex  │ │ BigQuery │ │  Manager   │
             │ worker     │ │ + filters  │ │        │ │          │ │            │
             └─────┬──────┘ └─────┬──────┘ └───┬────┘ └────┬─────┘ └────────────┘
                   ▼              ▼            ▼           ▼
             ┌──────────┐  ┌────────────────────────┐ ┌──────────┐
             │ GCS CMEK │  │ BM25 + Vertex AI       │ │ Logging/ │
             │ docs +   │  │ Vector Search          │ │ Monitor  │
             │ MM assets│  │ (metadata filters)     │ │          │
             └──────────┘  └────────────────────────┘ └──────────┘
```

**Later (not Phase 1):** Global HTTPS Load Balancer + Cloud Armor in front of `web`/`api`.

---

## 3. Cloud Run service responsibilities

| Service | Image / code | Responsibility |
|---------|--------------|----------------|
| **`web`** | `frontend/` | PWA UI only; calls `api`; no direct Vertex/GCS admin |
| **`api`** | `backend/` (API entry) | AuthN/Z, LangGraph query path, feedback API, signed asset URLs, health |
| **`ingest-worker`** | `backend/` (worker entry) | Parse/chunk/**multimodal extract**/embed/index; re-index jobs |

Each service has a **dedicated custom SA** (ADR-0005). Query path never blocks on full ingest.

### Health contract (all services that expose HTTP)

```json
{
  "status": "ok",
  "service": "erp-api",
  "version": "<git-sha-or-semver>",
  "deployed_at": "<ISO-8601 UTC>"
}
```

`/ready` may add dependency flags (vector, metadata store) without secrets.  
**Implementation note:** Phase 0 code placeholder should be updated in Phase 1 to match NFR-REL-03a (docs lock only in Gamma).

---

## 4. Logical component breakdown

### 4.1 Frontend (`frontend/` → service `web`)

| Component | Responsibility |
|-----------|----------------|
| **App shell** | Nav, auth gate, domain-denied state, offline banner |
| **Chat module** | Composer, messages, citations, **tables/images**, **StarRating** |
| **History module** | Session list/detail |
| **Admin module** | Upload, versions, jobs |
| **Analytics module** | KPIs including stars + cache hit % |
| **Voice module** | Mic/TTS controls; feature-flagged |
| **PWA layer** | Manifest, service worker, install affordances |
| **Design system** | shadcn/ui + domain components ([ui-specs.md](../ui-specs.md)) |

### 4.2 API (`backend/` → service `api`)

| Package / area | Responsibility |
|----------------|----------------|
| `api/` | HTTP: auth, chat/query, feedback, docs metadata, jobs status, analytics, voice, assets |
| `core/` | Settings, logging, security middleware, correlation IDs, version/deployed_at |
| `services/graph/` | **LangGraph** definition and node runners |
| `services/cache/` | Semantic cache get/set/invalidate |
| `services/retrieval/` | BM25 + Vertex Vector Search + **metadata filters** + RRF + ACL |
| `services/generation/` | Prompt assembly, Gemini, citation + multimodal refs |
| `services/guardrails/` | Input/output checks ([ADR-0004](../adr/0004-guardrails-architecture.md)) |
| `services/feedback/` | Star rating persistence + analytics emit |
| `services/analytics/` | BigQuery metadata events |
| `models/` | Pydantic schemas |

### 4.3 Ingest worker (`backend/` → service `ingest-worker`)

| Area | Responsibility |
|------|----------------|
| Parse | PDF/DOCX/MD/HTML |
| **Multimodal** | Table structure extraction; image assets + caption/OCR text |
| Chunk | Text (+ table text) chunks with metadata |
| Embed | Vertex embeddings |
| Index write | BM25 staging + **Vertex AI Vector Search** upsert with metadata |
| Versioning | Collaborate with publish/alias swap ([ADR-0003](../adr/0003-document-versioning.md)) |

Enqueue mechanism (Cloud Tasks vs Pub/Sub) remains a small open decision; **worker is Cloud Run**.

### 4.4 Data stores

| Store | Data | Notes |
|-------|------|-------|
| **GCS (CMEK)** | Raw files + multimodal assets per version | Immutable keys |
| **Metadata DB** | Docs, versions, ACL, jobs, sessions, feedback | **Firestore (Native mode)** — [ADR-0006](../adr/0006-metadata-store-firestore.md) |
| **Sparse index** | BM25 corpus per active set | Filter-aware |
| **Dense index** | **Vertex AI Vector Search** | Metadata filters locked requirement |
| **Semantic cache** | Query→response entries | Redis/Memorystore or equivalent TBD with Phase 3 design; can start in-process only for dev |
| **BigQuery** | Analytics facts | Hashed subject; stars; cache hits |
| **Secret Manager** | OAuth, model config | No SA JSON keys |

### 4.5 Cross-cutting

| Concern | Implementation sketch |
|---------|----------------------|
| AuthN | Google OAuth → domain allowlist → JWT/session |
| AuthZ | RBAC + ACL metadata filters |
| Security | Zero JSON keys; WIF/OIDC; defence-in-depth ([ADR-0005](../adr/0005-security-posture.md)) |
| Observability | JSON logs, metrics, correlation id, health version |
| Config | Env + Secret Manager; model IDs pinned per env |
| IaC | Terraform modules under `terraform/` |

---

## 5. LangGraph query path

```text
                    ┌─────────────────────────────────────────┐
                    │              LangGraph (api)              │
 START → authz_ok → input_guard → cache_lookup ─┬─ hit → output_guard → END
                    │                           │
                    │                        miss
                    │                           ▼
                    │              retrieve (metadata filters + hybrid + RRF)
                    │                           ▼
                    │                    grounding_gate
                    │                      │        │
                    │                   refuse    generate (Gemini)
                    │                      │        ▼
                    │                      │   package_citations_mm
                    │                      │        ▼
                    │                      └──▶ output_guard → cache_store? → END
                    └─────────────────────────────────────────┘
                              │
                              ▼
                         analytics + optional feedback (async client)
```

| Node | Responsibility |
|------|----------------|
| `input_guard` | Size, rate, injection heuristics |
| `cache_lookup` | Semantic cache by embedding + ACL + corpus fingerprint |
| `retrieve` | ACL + collection metadata filters → BM25 + Vector Search → RRF |
| `grounding_gate` | Refuse if insufficient evidence |
| `generate` | Gemini with docs-as-data prompt hygiene |
| `package_citations_mm` | Citations + table/image refs |
| `output_guard` | Citation id validation; ACL double-check |
| `cache_store` | Store only successful grounded answers when policy allows |

---

## 6. Metadata filtering & semantic caching

### 6.1 Metadata filtering (performance + security)

Applied at **index query time** (not only post-filter):

| Field (illustrative) | Purpose |
|----------------------|---------|
| `acl_labels` / principals | Security (mandatory) |
| `collection_id` | UX scope + smaller candidate set |
| `document_id` | Optional tight scope |
| `version_id` / `is_active` | Version integrity |

Correctness: zero out-of-filter chunks in results (NFR-PERF-07 / US-QA-08).

### 6.2 Semantic caching (P1)

| Concern | Rule |
|---------|------|
| Key | Embedding similarity bucket + ACL scope + collection + **corpus fingerprint** |
| Bust | On publish/retire affecting fingerprint; TTL backup |
| AuthZ | Re-validate principal on hit |
| Metrics | `cache.hit` / `cache.miss` |

---

## 7. Multimodal pipeline

```text
ingest-worker:
  file → parse → detect tables/images
       → store image assets (GCS version path)
       → table → structured text/HTML chunk(s)
       → image → caption/OCR text chunk + asset_id metadata
       → embed text representations → Vector Search + BM25
api generate/UI:
  answer may reference asset_id → UI fetches authorized URL → AnswerImage / AnswerTable
```

---

## 8. Ingestion & versioning path

See [ADR-0003](../adr/0003-document-versioning.md).

```text
Upload (api) → GCS raw/{document_id}/{version_id}/{filename}
  → Firestore Document + Version status=processing
  → extract text → chunk (~1000/150) → GCS processed/.../full.txt + chunks.jsonl
  → Firestore ready (pointers + text_preview) | failed  (Phase 2.3 ✓)
  → enqueue ingest-worker for embed/index  (later)
  → multimodal / embed / index (staging)
  → Publish → atomic activate → published (active)
  → invalidate semantic cache fingerprint for scope
  → Retire → remove from active retrieval
```

**Phase 2.1–2.3:** Upload + extract + chunk + processed storage. See [document-upload-api](../runbooks/document-upload-api.md).

---

## 9. Guardrails placement

See [ADR-0004](../adr/0004-guardrails-architecture.md). Integrated as LangGraph nodes (`input_guard`, `grounding_gate`, `output_guard`).

---

## 10. Analytics path (privacy-safe)

```text
Query completed / feedback submitted
  → event {
        event_id, ts, env, subject_hash,
        status, latency_*, model_id, tokens,
        collection_ids[], refusal_code?,
        cache_hit?, stars?, correlation_id
     }
  → BigQuery
```

**Not stored by default:** raw question, raw answer, document body.

---

## 11. Deployment view (target)

```text
              ┌──────────────────────────┐
              │ CI (OIDC) + WIF → GCP    │
              │ Zero JSON SA keys        │
              └────────────┬─────────────┘
                           │ images → Artifact Registry
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
 Cloud Run web      Cloud Run api     Cloud Run ingest-worker
   (SA-web)           (SA-api)            (SA-ingest)
        │                  │                  │
        └────────────┬─────┴────────┬─────────┘
                     ▼              ▼
              Secret Manager   Cloud Monitoring
                     │
                     ▼
         Vertex AI · Vector Search · GCS · BQ
```

Environments supply `gcp_project_id` via tfvars (not committed secrets).

---

## 12. Repository mapping

| Path | Architecture slice |
|------|--------------------|
| `frontend/` | PWA → service **web** |
| `backend/app/api` | HTTP edge → service **api** |
| `backend/app/services/graph` | LangGraph |
| `backend/` worker entry | service **ingest-worker** |
| `terraform/` | GCP resources + SAs + WIF |
| `docs/*` | Contracts |

---

## 13. Open decisions (tracked)

| Topic | Tracking | Target |
|-------|----------|--------|
| ~~Firestore vs Cloud SQL for metadata~~ | **Resolved** | [ADR-0006](../adr/0006-metadata-store-firestore.md) — Firestore Native |
| Exact embedding model + dimensions | BL-DEC-02 | ADR-0007 |
| Vector Search index topology (shards, filters schema) | BL-DEC-03 | ADR-0007 |
| Semantic cache store (Memorystore vs other) | BL-DEC-06 | Phase 3 design |
| STT/TTS provider | BL-DEC-04 | Phase 5 ADR |
| Ingest enqueue: Cloud Tasks vs Pub/Sub | BL-DEC-05 | Phase 2 |
| Streaming tokens to client | BL-RAG-08 | Phase 3+ |
| HTTPS LB + Cloud Armor | deferred | Pre-prod hardening |

**Locked:** LangGraph; Vertex AI Vector Search; services api/ingest-worker/web; zero JSON keys + WIF.

---

## 14. Related documents

- [requirements.md](../requirements.md) (v3 Gamma)  
- [ui-specs.md](../ui-specs.md)  
- [backlog.md](../backlog.md)  
- [grok-three-agent-protocol.md](../grok-three-agent-protocol.md)  
