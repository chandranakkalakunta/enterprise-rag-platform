# Enterprise RAG Platform

Production-grade **Enterprise Retrieval-Augmented Generation** on Google Cloud Platform: grounded answers with citations, document versioning, guardrails, PWA UX, optional voice, multimodal evidence (tables/images), and privacy-safe analytics.

**Owner:** Chandra AI Labs (`chandraailabs.com`)  
**Status:** **Phase 3 Complete** — retrieval MVP + grounded answer; **next: Phase 5 (PWA/UI), then Phase 4 (RAG quality)**  
**GCP project:** set via `var.gcp_project_id` / `GCP_PROJECT_ID` (never hard-coded in app code)  
**Project ID:** `enterprise-rag-platform-502711` (number `642114828076`)  

**Audience (auth allowlist):** `chandraailabs.com` + `gmail.com`  
**Stack:** Next.js **PWA** (no native apps) · shadcn/ui · FastAPI · **LangGraph** · Vertex AI Gemini + **Vector Search** · Terraform · Cloud Run (`rag-api`, `rag-ingest`, `rag-web`)

---

## Phase progress

| Phase | Focus | Status |
|-------|--------|--------|
| **0** | Foundation & requirements lock | ✅ **Complete** |
| **0.1** | GCP project ID switch | ✅ **Complete** |
| **1** | **GCP Foundation** (1.1–1.7) | ✅ **Complete** (PRs #3–#9) |
| **2** | **Ingestion MVP** (upload → extract → chunk → publish/retire) | ✅ **Complete** (PRs #11–#15) |
| **3** | **Retrieval MVP** (embed → Vector Search → search + grounded answer) | ✅ **Complete** (PRs #17–#22) |
| **3.0–3.4** | ADRs, embeddings, index, search API, LangGraph+Gemini answer | ✅ **Complete** |
| **5** | Voice + **full PWA** (desktop/tablet/mobile browser + installable) | 🔜 **Next major track** — **no native apps** |
| **4** | Multi-turn, ACL depth, hybrid/RRF, fuller guardrails | Planned **after Phase 5** |
| **6** | Analytics, eval gates, cost dashboards | Planned |

### Delivery order (post–Phase 3)

1. **Phase 5** — full responsive PWA / UI (chat, admin, citations UI)  
2. **Phase 4** — RAG quality (hybrid BM25+RRF, multi-turn, ACL, fuller guards)  
3. **Phase 6** — analytics / evaluation / Binary Auth  

Full index: [docs/phases.md](docs/phases.md)  
Phase 0: [retro](docs/retrospectives/phase-0.md) · [report](docs/reports/phase-0-engineering-report.md)  
Phase 1: [retro](docs/retrospectives/phase-1.md) · [report](docs/reports/phase-1-engineering-report.md)  
Phase 2: [retro](docs/retrospectives/phase-2.md) · [report](docs/reports/phase-2-engineering-report.md)  
Phase 3: [retro](docs/retrospectives/phase-3.md) · [report](docs/reports/phase-3-engineering-report.md)

### Core APIs (backend MVP)

```text
POST /api/v1/documents/upload
POST /api/v1/documents/{id}/versions/{vid}/publish
POST /api/v1/documents/{id}/versions/{vid}/retire
POST /api/v1/query/search
POST /api/v1/query/answer
```

Runbooks: [upload](docs/runbooks/document-upload-api.md) · [lifecycle](docs/runbooks/version-lifecycle.md) · [vector-search](docs/runbooks/vector-search.md) · [dense-search](docs/runbooks/dense-search-api.md) · [grounded-answer](docs/runbooks/grounded-answer-api.md)

### Phase 3 retrieval decisions

- [ADR-0007](docs/adr/0007-embedding-and-vector-search.md) — Vertex embeddings + Vector Search; embed on **ready**, activate on **publish**  
- [ADR-0008](docs/adr/0008-retrieval-and-grounded-generation.md) — LangGraph dense retrieve → evidence check → Gemini; `top_k=5`, temperature `0.2`  

---

## Architecture (high level)

```
  web (Next.js PWA) ──JWT──▶ api (FastAPI + LangGraph)
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ingest-worker    Vertex Vector     BigQuery
        (async MM+index) Search + BM25     (metadata only)
```

Details: [docs/architecture/overview.md](docs/architecture/overview.md) · ADRs [0001](docs/adr/0001-high-level-architecture.md)–[0008](docs/adr/0008-retrieval-and-grounded-generation.md)

---

## Documentation map

| Doc | Purpose |
|-----|---------|
| [docs/requirements.md](docs/requirements.md) | Personas, user stories, NFRs (v3 locked) |
| [docs/ui-specs.md](docs/ui-specs.md) | Screens, PWA, voice, StarRating, multimodal, shadcn/ui |
| [docs/architecture/overview.md](docs/architecture/overview.md) | Services, LangGraph, cache, multimodal |
| [docs/adr/](docs/adr/) | Architecture Decision Records (0001–0008) |
| [docs/backlog.md](docs/backlog.md) | Living backlog |
| [docs/phases.md](docs/phases.md) | Phase index + delivery order |
| [docs/grok-three-agent-protocol.md](docs/grok-three-agent-protocol.md) | How we build |
| [docs/retrospectives/](docs/retrospectives/) | Phase retrospectives |
| [docs/reports/](docs/reports/) | Engineering reports |
| [CHANGELOG.md](CHANGELOG.md) | Change history |

---

## Repository layout

```
enterprise-rag-platform/
├── backend/          # FastAPI + LangGraph (api / ingest-worker)
├── frontend/         # Next.js PWA (web)
├── terraform/        # GCP IaC (var.gcp_project_id)
├── docs/             # Requirements, ADRs, backlog, retros, reports
├── scripts/          # Ops scripts (later)
├── config/           # Non-secret samples
├── CHANGELOG.md
└── README.md
```

---

## Local development (quick start)

**Requirements:** Python **3.12** (not 3.14), Node **22**, optional Terraform ≥ 1.5.

### Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip check
uvicorn app.main:app --reload --port 8000
```

- Health: http://localhost:8000/health  
- Ready: http://localhost:8000/ready  
- OpenAPI: http://localhost:8000/docs  

Both return `status`, `service` (`rag-api`), `version` (`APP_VERSION`, default `dev`), and `deployed_at` (`DEPLOYED_AT`, default `""`). Set both env vars at Cloud Run deploy.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

### Config

```bash
cp .env.example .env
# Set GCP_PROJECT_ID, VECTOR_SEARCH_*, GENERATION_MODEL_ID for live query path
```

Never commit secrets. Production secrets live in Secret Manager.
