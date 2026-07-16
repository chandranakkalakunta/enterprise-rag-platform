# Enterprise RAG Platform

Production-grade **Enterprise Retrieval-Augmented Generation** on Google Cloud Platform: grounded answers with citations, document versioning, guardrails, PWA UX, optional voice, multimodal evidence (tables/images), and privacy-safe analytics.

**Owner:** Chandra AI Labs (`chandraailabs.com`)  
**Status:** **Phase 0 Complete — Requirements Locked**  
**PR:** [#1 — Phase 0: Project Foundation](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/1)  
**GCP project:** `var.gcp_project_id` / `GCP_PROJECT_ID` (never hard-coded)  
**Audience (auth allowlist):** `chandraailabs.com` + `gmail.com`  
**Stack:** Next.js PWA · shadcn/ui · FastAPI · **LangGraph** · Vertex AI Gemini + **Vector Search** · Terraform · Cloud Run (`api`, `ingest-worker`, `web`)

---

## Phase progress

| Phase | Focus | Status |
|-------|--------|--------|
| **0** | Foundation & requirements lock | ✅ **Complete** |
| **1** | GCP foundation, auth, WIF CI, health metadata | 🔜 Next |
| **2** | Ingestion & document versioning | Planned |
| **3** | Hybrid RAG, citations, guardrails, 5-star feedback | Planned |
| **4** | Multi-turn, ACL depth, safety tuning | Planned |
| **5** | Voice + PWA install/offline | Planned |
| **6** | Analytics, eval gates, cost dashboards | Planned |

Full index: [docs/phases.md](docs/phases.md)  
Phase 0 retrospective: [docs/retrospectives/phase-0.md](docs/retrospectives/phase-0.md)  
Phase 0 engineering report: [docs/reports/phase-0-engineering-report.md](docs/reports/phase-0-engineering-report.md)

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

Details: [docs/architecture/overview.md](docs/architecture/overview.md) · ADRs [0001](docs/adr/0001-high-level-architecture.md)–[0005](docs/adr/0005-security-posture.md)

---

## Documentation map

| Doc | Purpose |
|-----|---------|
| [docs/requirements.md](docs/requirements.md) | Personas, user stories, NFRs (v3 locked) |
| [docs/ui-specs.md](docs/ui-specs.md) | Screens, PWA, voice, StarRating, multimodal, shadcn/ui |
| [docs/architecture/overview.md](docs/architecture/overview.md) | Services, LangGraph, cache, multimodal |
| [docs/adr/](docs/adr/) | Architecture Decision Records (0001–0005) |
| [docs/backlog.md](docs/backlog.md) | Living backlog |
| [docs/phases.md](docs/phases.md) | Phase index |
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
├── terraform/        # GCP IaC skeleton (var.gcp_project_id)
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
- OpenAPI: http://localhost:8000/docs  

> Phase 1 will add `version` + `deployed_at` to `/health` and `/ready` (already required in NFRs).

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
# set GCP_PROJECT_ID and other local values — never commit .env
```

### Terraform (skeleton only in Phase 0)

```bash
cd terraform
# copy environments/dev/terraform.tfvars.example → terraform.tfvars (gitignored)
# terraform init / plan in Phase 1 after APIs and backend state exist
```

---

## Security highlights

- **Zero JSON service-account keys** — WIF/OIDC for CI; runtime uses attached Cloud Run SAs ([ADR-0005](docs/adr/0005-security-posture.md))
- Secrets in **Secret Manager** only; `.env` gitignored
- Least-privilege **custom SAs** per service (`api`, `ingest-worker`, `web`)
- CMEK on data stores (from foundation phase)
- Non-root containers (uid/gid **1001**)
- No PII in logs/analytics by default (hashed subject IDs)
- Auth domain allowlist: `chandraailabs.com`, `gmail.com`

---

## Contributing / protocol

We follow the **Grok Three-Agent Protocol** ([docs/grok-three-agent-protocol.md](docs/grok-three-agent-protocol.md)):

- Feature branches only — never push feature work directly to `main`
- ADRs for significant decisions
- Living `docs/backlog.md` and `CHANGELOG.md`
- Root cause over silent workarounds
- Fail-fast verification every phase

---

## License

Proprietary — **Chandra AI Labs** / project owner.
