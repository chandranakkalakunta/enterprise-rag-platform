# ADR-0002: Technology Stack & Toolchain

## Status

Accepted — 2026-07-16  
**Amended:** 2026-07-16 (Phase 0 Beta) — locked **shadcn/ui** + UX contract `docs/ui-specs.md`.  
**Amended:** 2026-07-16 (Phase 0 Gamma) — locked **LangGraph** orchestration, **Vertex AI Vector Search**, multimodal notes, three Cloud Run services.

## Context

Phase 0 must lock a coherent stack for the Enterprise RAG Platform before feature work begins. Stack choices must support:

- FastAPI backend services and RAG pipelines in Python
- **LangGraph** for explicit, testable query orchestration
- Next.js PWA frontend (chat, voice, admin, feedback, multimodal render)
- Terraform for GCP (`var.gcp_project_id` — set via tfvars; current dev example `enterprise-rag-platform-502711`; never hard-code in application code)
- Reproducible dependency pins for CI
- Production non-negotiables: non-root containers, Secret Manager, structured JSON logs, **zero JSON SA keys**, WIF/OIDC

## Decision

### Backend
| Item | Choice |
|------|--------|
| Language | Python 3.12 |
| Framework | FastAPI |
| Orchestration | **LangGraph** (query graph: guard → retrieve → ground → generate → post-check) |
| Validation / settings | Pydantic v2 |
| ASGI server | Uvicorn |
| Package pinning | `requirements.txt` with pinned versions (+ optional `pyproject.toml` for packaging metadata) |
| Testing | pytest, httpx, pytest-cov |

### Frontend
| Item | Choice |
|------|--------|
| Framework | Next.js 15 (App Router) + TypeScript |
| UI | React 19 (as shipped with Next) |
| Design system | **shadcn/ui** + Tailwind CSS + Lucide icons |
| Forms (recommended) | React Hook Form + Zod |
| PWA | `@ducanh2912/next-pwa` or next-pwa-compatible setup (wired in later phase) |
| Package manager | npm (lockfile committed); pnpm optional later if monorepo workspaces demand it |
| Node | 22 LTS |
| UX contract | `docs/ui-specs.md` |

### AI / RAG
| Item | Choice |
|------|--------|
| LLM | Vertex AI Gemini (e.g. gemini-2.5-flash class; exact model ID pinned per env) |
| Embeddings | Vertex AI text embedding models (version pinned in config) |
| Vector index | **Vertex AI Vector Search** (**locked** — not “or equivalent” for MVP) |
| Sparse retrieval | rank-bm25 (or equivalent) for v1 hybrid |
| Fusion | Reciprocal Rank Fusion (RRF) |
| Metadata filtering | Restrict filters on vector + sparse queries (ACL, collection, active version) |
| Semantic cache | Optional layer (P1) keyed by embedding + ACL + corpus fingerprint |
| Multimodal | Extract tables/images at ingest; store assets in GCS; render in UI; embed text/OCR/captions for retrieval |

### Data & Platform
| Item | Choice |
|------|--------|
| Object storage | GCS (CMEK) |
| Metadata store | **Open** — Firestore vs Cloud SQL deferred (BL-DEC-01 / future ADR) |
| Analytics | BigQuery (hashed user IDs, metadata only; star ratings aggregates) |
| Secrets | Secret Manager |
| Auth (v1) | Google OAuth; allowlist `chandraailabs.com` + `gmail.com` |
| Compute | Cloud Run services: **`api`**, **`ingest-worker`**, **`web`** |
| Edge / WAF | HTTPS LB + Cloud Armor **later** (not Phase 1) |
| IaC | Terraform >= 1.5, Google provider |
| CI | Cloud Build and/or GitHub Actions + **Workload Identity Federation** (no JSON keys) |

### Runtime / Containers
| Item | Choice |
|------|--------|
| Backend base image | `python:3.12-slim` multi-stage |
| Frontend image | Node build → Next standalone (or nginx) on Cloud Run **web** |
| Container user | non-root uid/gid 1001 |
| Health | `/health` + `/ready` return `version` + `deployed_at` |

### Architectural Principles (mandatory)
1. **Stateless services** — no in-memory session affinity; JWT/auth externalized  
2. **No secrets in code or committed `.env`** — `.env.example` only; Secret Manager in deploy  
3. **Zero JSON SA keys** — WIF/OIDC + runtime metadata SA only ([ADR-0005](./0005-security-posture.md))  
4. **Pinned dependencies** — CI installs only from lock/requirements files  
5. **Structured JSON logging** — Cloud Logging compatible; no PII in logs  
6. **Idempotent infra** — Terraform and scripts safe to re-run  
7. **LangGraph for query orchestration** — explicit nodes, testable edges  

## Rationale

- **Python + FastAPI** is the default for production RAG on GCP (Vertex SDKs, async I/O, OpenAPI).  
- **LangGraph** makes multi-step RAG (cache → retrieve → ground → generate → feedback hooks) explicit and unit-testable vs ad-hoc call chains.  
- **Vertex AI Vector Search** is locked for managed ANN, IAM alignment, and metadata filters.  
- **Three Cloud Run services** separate query latency path (`api`) from heavy ingest (`ingest-worker`) and static/SSR UI (`web`).  
- **shadcn/ui** provides accessible primitives for chat, tables, and star ratings.  
- **requirements.txt pins** match production non-negotiable for CI hermetic installs.  
- **Terraform + WIF** keep infra and deploy keyless.

## Consequences

### Positive
- Clear orchestration and service boundaries  
- Strong GCP integration and IAM story  
- Multimodal and feedback fit the same stack  
- Reproducible installs and infra  

### Negative
- LangGraph adds a dependency and learning curve  
- Multimodal increases ingest complexity and storage  
- Next.js operational surface larger than pure static SPA  
- Python cold starts on Cloud Run  

### Risks and Mitigations
- **Risk:** Model deprecation / ID change  
  - **Mitigation:** Model IDs in config/Secret Manager; ADR when changing  
- **Risk:** Frontend SSR secrets leakage  
  - **Mitigation:** Public env vars only for browser; server-only secrets never prefixed `NEXT_PUBLIC_`  
- **Risk:** Dependency drift  
  - **Mitigation:** Pin all packages; `pip check` in CI; renovate/manual bumps via PR  
- **Risk:** Semantic cache serves stale post-publish answers  
  - **Mitigation:** Corpus fingerprint + event invalidation (US-QA-07)  

## Alternatives Rejected

### Backend: Node.js / NestJS only
- Why rejected: Weaker fit for RAG/ML libraries and Vertex Python tooling as primary path

### Orchestration: ad-hoc Python functions only
- Why rejected: Harder to test, observe, and evolve multi-step RAG with cache/guard nodes

### Frontend: Vite SPA only (no Next.js)
- Why rejected: Phase goals include PWA + richer routing for enterprise auth; Next.js is the specified stack

### Frontend: Heavy proprietary component kits
- Why rejected: Less portable; shadcn keeps components owned in-repo

### Vector DB: Self-hosted from day one
- Why rejected: Vertex AI Vector Search locked for MVP

### Compute: GKE first
- Why rejected: Three Cloud Run services sufficient; revisit if mesh complexity appears

### CI: JSON SA keys in secrets
- Why rejected: Explicitly forbidden (ADR-0005)

## References

- [ADR-0001 High-Level Architecture](./0001-high-level-architecture.md)  
- [ADR-0005 Security Posture](./0005-security-posture.md)  
- [UI specs](../ui-specs.md)  
- [Architecture overview](../architecture/overview.md)  
- FastAPI: https://fastapi.tiangolo.com  
- LangGraph: https://langchain-ai.github.io/langgraph/  
- Next.js: https://nextjs.org/docs  
- shadcn/ui: https://ui.shadcn.com  
- Vertex AI Vector Search: https://cloud.google.com/vertex-ai/docs/vector-search/overview  
- Terraform Google provider: https://registry.terraform.io/providers/hashicorp/google/latest/docs  
