# ADR-0001: High-Level Architecture — Enterprise RAG Platform

## Status

Accepted — 2026-07-16  
**Amended:** 2026-07-16 (Phase 0 Beta) — cross-links to overview, versioning (ADR-0003), guardrails (ADR-0004); no change to core decision.

## Context

We are building a production-grade Enterprise RAG (Retrieval-Augmented Generation) platform on Google Cloud Platform. The target project is supplied at apply time via Terraform variable `var.gcp_project_id` / env `GCP_PROJECT_ID` (never hard-coded in application code). Current dev example: `enterprise-rag-platform-502711`. The system must support:

1. **Document Q&A** with citations over versioned enterprise corpora
2. **PWA UI** for web and installable mobile experience
3. **Voice** input/output for hands-free querying
4. **Document versioning** with auditability of which version answered a query
5. **Analytics** (usage, quality, cost) without logging PII or raw query text where avoidable
6. **Guardrails** (safety, grounding, PII redaction, access control)
7. **GCP-native** operations: least-privilege IAM, Secret Manager, CMEK, structured logging

Selection criteria (priority order):
1. Production operability on GCP with least-privilege and compliance posture
2. Retrieval quality (hybrid search, citations, version-aware answers)
3. Latency (p50/p95/p99 tracked; interactive chat and voice)
4. Cost control (scale-to-zero where possible; token and index cost visibility)
5. Maintainability for a small team growing over phases
6. Career alignment: Python + GCP + production ML systems

## Decision

### Architecture Style
- **Monorepo** with clear boundaries: `frontend/`, `backend/`, `terraform/`, `docs/`
- **Stateless API services** on Cloud Run (no local state; all durable state external)
- **Async ingestion pipeline** decoupled from query path (upload → parse → chunk → embed → index)
- **Hybrid retrieval**: sparse (BM25 / keyword) + dense (Vertex AI embeddings + vector index), fused with Reciprocal Rank Fusion (RRF)
- **Generation** via Vertex AI Gemini with grounded prompts, mandatory citations, and guardrail layers
- **IaC-first**: all GCP resources via Terraform; no click-ops for production paths

### Logical Components

```
┌─────────────────────────────────────────────────────────────────┐
│  PWA (Next.js) — Chat UI, Voice, Admin, Analytics dashboards    │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS / JWT
┌────────────────────────────▼────────────────────────────────────┐
│  API Gateway surface (Cloud Run — FastAPI)                      │
│  AuthZ · Rate limit · Guardrails · Query / Ingest / Admin APIs  │
└───┬──────────────┬──────────────┬──────────────┬────────────────┘
    │              │              │              │
    ▼              ▼              ▼              ▼
 Ingestion      Retrieval      Generation     Analytics
 (parse/chunk)  (hybrid+RRF)   (Gemini)       (BigQuery)
    │              │              │              │
    ▼              ▼              ▼              ▼
 GCS + meta    Vector index   Vertex AI     BQ (hashed IDs,
 (versions)    + BM25 store   Gemini        metadata only)
```

### Data Plane (high level)
| Concern | Service |
|---------|---------|
| Raw docs & versions | Cloud Storage (CMEK) |
| Document / chunk metadata | **Firestore (Native mode)** — [ADR-0006](./0006-metadata-store-firestore.md) |
| Dense vectors | Vertex AI Vector Search (or matching managed index) |
| Sparse index | In-process BM25 for v1; evaluate managed search later |
| Secrets | Secret Manager |
| Identity | Google Identity / OAuth (enterprise SSO path later) |
| Observability | Cloud Logging (JSON) + Cloud Monitoring + BigQuery query log |

### Deployment Topology
- **Region:** asia-south1 (primary; override via Terraform variables — never hardcode in app code)
- **Compute:** Cloud Run for API + frontend static/SSR container
- **CI/CD:** Cloud Build + WIF (keyless) in later phase
- **Environments:** `dev` first (`var.gcp_project_id` via tfvars); staging/prod via Terraform workspaces/envs later

## Rationale

- **Cloud Run + stateless FastAPI** matches bursty Q&A traffic, minimizes ops vs GKE, and pairs with Python ML/RAG ecosystem.
- **Hybrid retrieval** is proven for enterprise policy/HR corpora (keyword codes + semantic paraphrase); pure vector search is insufficient for exact terms.
- **Decoupled ingestion** keeps query latency independent of heavy parse/embed work and supports versioning/reindex jobs.
- **BigQuery analytics with hashed identifiers** supports product metrics without storing PII in analytics tables.
- **Monorepo + Terraform** keeps ADRs, code, and infra reviewable in one PR workflow (Three-Agent Protocol).

## Consequences

### Positive
- Clear service boundaries for phased delivery (ingest → retrieve → generate → voice → analytics)
- GCP-native security and observability from day one
- Hybrid RAG path aligns with prior production HR RAG learnings
- Scale-to-zero reduces idle cost in early phases

### Negative
- Cold starts on Cloud Run (mitigate with min instances in prod later)
- Hybrid index consistency (BM25 + vector) requires careful reindex on version publish
- Monorepo CI must path-filter to avoid full rebuilds later

### Risks and Mitigations
- **Risk:** Vector index + BM25 drift after version publish
  - **Mitigation:** Versioned index aliases; atomic “publish” that swaps active version pointer after both stores ready
- **Risk:** Grounding failures / hallucinations
  - **Mitigation:** Guardrails ADR path; refuse when retrieval confidence low; always cite chunks
- **Risk:** Cost blowups from embeddings/LLM
  - **Mitigation:** Token budgets, caching frequent queries, BigQuery cost dashboards

## Alternatives Rejected

### GKE microservices from day one
- Why rejected: Operational overhead not justified before product-market validation of RAG quality and UX

### Pure managed “RAG-as-a-service” only (no custom pipeline)
- Why rejected: Insufficient control over versioning, guardrails, hybrid retrieval, and enterprise analytics

### Self-hosted vector DB (e.g. Qdrant/Weaviate on GCE/GKE) in Phase 0
- Why rejected: Prefer managed Vertex AI path first; re-evaluate if latency/cost/features force it

### Separate repos for frontend/backend/infra
- Why rejected: Slows ADR↔code↔infra coherence required by the engineering protocol

## References

- [ADR-0002 Tech Stack](./0002-tech-stack.md) (LangGraph, Vector Search, three Cloud Run services)
- [ADR-0003 Document Versioning](./0003-document-versioning.md)
- [ADR-0004 Guardrails Architecture](./0004-guardrails-architecture.md)
- [ADR-0005 Security Posture](./0005-security-posture.md)
- [ADR-0006 Metadata Store — Firestore](./0006-metadata-store-firestore.md)  
- [ADR-0007 Embedding & Vector Search](./0007-embedding-and-vector-search.md)  
- [ADR-0008 Retrieval & Grounded Generation](./0008-retrieval-and-grounded-generation.md)  
- [ADR-0009 AuthN/AuthZ and User Profiles](./0009-authn-authz-user-profiles.md)  
- [ADR-0010 PWA Shell and Version Auto-Reload](./0010-pwa-shell-version-reload.md)  
- [ADR-0011 RAG Evaluation and Hybrid Retrieval](./0011-rag-evaluation-and-hybrid-retrieval.md)  
- [ADR-0012 Production Edge — HTTPS LB + IAP](./0012-production-edge-lb-iap.md)
- [Architecture overview (diagrams & components)](../architecture/overview.md)
- [Requirements](../requirements.md) · [UI specs](../ui-specs.md)
- Enterprise HR RAG production patterns (hybrid + RRF + PII-free BigQuery)
- Vertex AI Gemini / Vector Search docs
- Three-Agent Engineering Protocol (project adaptation: `docs/grok-three-agent-protocol.md`)
