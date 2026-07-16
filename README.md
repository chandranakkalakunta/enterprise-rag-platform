# Enterprise RAG Platform

Production-grade Enterprise RAG on Google Cloud Platform.

**GCP project:** `var.gcp_project_id` (set via tfvars / `GCP_PROJECT_ID`; never hard-coded)  
**Phase:** 0 Gamma — Requirements locked (docs complete)  
**Stack:** Next.js PWA · shadcn/ui · FastAPI · LangGraph · Vertex AI Gemini + Vector Search · Terraform · Cloud Run (`api`, `ingest-worker`, `web`)  
**Audience:** `chandraailabs.com` + `gmail.com`

---

## Architecture (high level)

```
  web (Next.js PWA) ──JWT──▶ api (FastAPI + LangGraph)
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ingest-worker    Vertex Vector     BigQuery
        (async MM+index) Search + BM25     (metadata)
```

See [docs/architecture/overview.md](docs/architecture/overview.md), [docs/requirements.md](docs/requirements.md) (v3), and ADRs 0001–0005.

---

## Repository layout

```
enterprise-rag-platform/
├── backend/          # FastAPI API + RAG services
├── frontend/         # Next.js PWA
├── terraform/        # GCP infrastructure (skeleton in Phase 0)
├── docs/             # Requirements, ADRs, backlog, protocol, runbooks
├── scripts/          # Idempotent ops scripts (later)
├── config/           # Non-secret config samples
├── CHANGELOG.md
└── README.md
```

---

## Quick start (local)

### Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip check
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Copy `.env.example` → `.env` for local overrides. **Never commit `.env`.**

---

## Documentation map

| Doc | Purpose |
|-----|---------|
| [docs/requirements.md](docs/requirements.md) | Personas, stories, NFRs (v3 Gamma lock) |
| [docs/ui-specs.md](docs/ui-specs.md) | Screens, PWA, voice, feedback, multimodal, shadcn/ui |
| [docs/architecture/overview.md](docs/architecture/overview.md) | Services, LangGraph, cache, multimodal |
| [docs/adr/](docs/adr/) | ADRs 0001–0005 (incl. security posture) |
| [docs/backlog.md](docs/backlog.md) | Living backlog (deferrals + completions) |
| [docs/grok-three-agent-protocol.md](docs/grok-three-agent-protocol.md) | How we build (v1.0) |
| [CHANGELOG.md](CHANGELOG.md) | Release / PR history |

---

## Engineering protocol

We follow the **Grok Three-Agent Protocol** (project adaptation v1.0):

- Feature branches only — never push feature work to `main`
- ADRs for significant decisions
- Living `docs/backlog.md` and `CHANGELOG.md`
- Root cause over silent workarounds
- Fail-fast verification every phase

---

## Phase roadmap (summary)

| Phase | Focus |
|-------|--------|
| **0** | Foundation, docs, ADRs, skeletons |
| **1** | GCP foundation, auth, CI skeleton |
| **2** | Ingestion & document versioning |
| **3** | Hybrid RAG + citations + guardrails baseline |
| **4** | Multi-turn, ACL depth, safety tuning |
| **5** | Voice + PWA |
| **6** | Analytics, evaluation gates, cost dashboards |

Details: [docs/requirements.md](docs/requirements.md) · [docs/backlog.md](docs/backlog.md)

---

## Security non-negotiables

- Secrets in **Secret Manager** only
- Least-privilege service accounts
- CMEK on data stores (from foundation phase)
- Non-root containers (uid/gid 1001)
- No PII in logs (hash user identifiers)
- Structured JSON logging

---

## License

Proprietary — Chandra AI Labs / project owner.
