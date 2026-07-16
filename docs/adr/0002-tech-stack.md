# ADR-0002: Technology Stack & Toolchain

## Status

Accepted — 2026-07-16

## Context

Phase 0 must lock a coherent stack for the Enterprise RAG Platform before feature work begins. Stack choices must support:

- FastAPI backend services and RAG pipelines in Python
- Next.js PWA frontend (chat, voice, admin)
- Terraform for GCP (`sport-slot-dev`)
- Reproducible dependency pins for CI
- Production non-negotiables: non-root containers, Secret Manager, structured JSON logs, no secrets in repo

## Decision

### Backend
| Item | Choice |
|------|--------|
| Language | Python 3.12 |
| Framework | FastAPI |
| Validation / settings | Pydantic v2 |
| ASGI server | Uvicorn |
| Package pinning | `requirements.txt` with pinned versions (+ optional `pyproject.toml` for packaging metadata) |
| Testing | pytest, httpx, pytest-cov |

### Frontend
| Item | Choice |
|------|--------|
| Framework | Next.js 15 (App Router) + TypeScript |
| UI | React 19 (as shipped with Next) |
| Styling | Tailwind CSS (placeholder; design system later) |
| PWA | `@ducanh2912/next-pwa` or next-pwa-compatible setup (wired in later phase) |
| Package manager | npm (lockfile committed); pnpm optional later if monorepo workspaces demand it |
| Node | 22 LTS |

### AI / RAG
| Item | Choice |
|------|--------|
| LLM | Vertex AI Gemini (e.g. gemini-2.5-flash class; exact model ID pinned per env) |
| Embeddings | Vertex AI text embedding models (version pinned in config) |
| Vector index | Vertex AI Vector Search (or equivalent managed) |
| Sparse retrieval | rank-bm25 (or equivalent) for v1 hybrid |
| Fusion | Reciprocal Rank Fusion (RRF) |

### Data & Platform
| Item | Choice |
|------|--------|
| Object storage | GCS (CMEK) |
| Metadata store | Firestore (default for v1; Cloud SQL if relational needs dominate — later ADR) |
| Analytics | BigQuery (hashed user IDs, metadata only) |
| Secrets | Secret Manager |
| Auth (v1) | Google OAuth / Identity Platform path |
| Compute | Cloud Run |
| IaC | Terraform >= 1.5, Google provider |
| CI (later) | Cloud Build + Workload Identity Federation |

### Runtime / Containers
| Item | Choice |
|------|--------|
| Backend base image | `python:3.12-slim` multi-stage |
| Frontend image | Node build → nginx or Next standalone on Cloud Run |
| Container user | non-root uid/gid 1001 |

### Architectural Principles (mandatory)
1. **Stateless services** — no in-memory session affinity; JWT/auth externalized
2. **No secrets in code or committed `.env`** — `.env.example` only; Secret Manager in deploy
3. **Pinned dependencies** — CI installs only from lock/requirements files
4. **Structured JSON logging** — Cloud Logging compatible; no PII in logs
5. **Idempotent infra** — Terraform and scripts safe to re-run

## Rationale

- **Python + FastAPI** is the default for production RAG on GCP (Vertex SDKs, async I/O, OpenAPI).
- **Next.js** provides App Router, SSR/SSG options, and a clear PWA path for enterprise chat UX.
- **Vertex AI** keeps data path and IAM inside GCP; reduces multi-cloud key sprawl.
- **requirements.txt pins** match Chandra’s production non-negotiable for CI hermetic installs.
- **Terraform** is the standard for reviewable, idempotent GCP foundation.

## Consequences

### Positive
- Single language for API + RAG orchestration
- Strong GCP integration and IAM story
- Clear frontend path to PWA and voice UI later
- Reproducible installs and infra

### Negative
- Next.js operational surface larger than pure static SPA
- Python cold starts on Cloud Run
- Vertex AI regional/model availability must be validated per region

### Risks and Mitigations
- **Risk:** Model deprecation / ID change
  - **Mitigation:** Model IDs in config/Secret Manager; ADR when changing
- **Risk:** Frontend SSR secrets leakage
  - **Mitigation:** Public env vars only for browser; server-only secrets never prefixed `NEXT_PUBLIC_`
- **Risk:** Dependency drift
  - **Mitigation:** Pin all packages; `pip check` in CI; renovate/manual bumps via PR

## Alternatives Rejected

### Backend: Node.js / NestJS only
- Why rejected: Weaker fit for RAG/ML libraries and Vertex Python tooling as primary path

### Frontend: Vite SPA only (no Next.js)
- Why rejected: Phase goals include PWA + richer routing/SSR options for enterprise auth and SEO-free but installable app; Next.js is the specified stack for this project

### Package managers: Poetry-only without requirements.txt
- Why rejected: CI non-negotiable is install from requirements.txt with pins; pyproject may coexist for metadata

### Vector DB: Self-hosted from day one
- Why rejected: Prefer managed Vertex index until proven otherwise (see ADR-0001)

### Compute: GKE first
- Why rejected: Cloud Run sufficient for Phase 0–N; revisit if multi-service mesh complexity appears

## References

- ADR-0001 High-Level Architecture
- FastAPI: https://fastapi.tiangolo.com
- Next.js: https://nextjs.org/docs
- Vertex AI: https://cloud.google.com/vertex-ai/docs
- Terraform Google provider: https://registry.terraform.io/providers/hashicorp/google/latest/docs
