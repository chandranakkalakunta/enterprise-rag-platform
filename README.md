# Enterprise RAG Platform

Production-grade **Enterprise Retrieval-Augmented Generation** on Google Cloud Platform: grounded answers with citations, document versioning, guardrails, PWA UX, optional voice, multimodal evidence (tables/images), and privacy-safe analytics.

**Owner:** Chandra AI Labs (`chandraailabs.com`)  
**Status:** **Phase 2 Complete** — ingestion MVP lifecycle live; **Phase 3 next** (retrieval)  
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
| **2.0–2.4** | ADR-0006, upload, Firestore, chunking, lifecycle | ✅ **Complete** |
| **3** | Hybrid RAG, citations, guardrails, 5-star feedback | 🔜 **Next** |
| **4** | Multi-turn, ACL depth, safety tuning | Planned |
| **5** | Voice + **full PWA** (desktop/tablet/mobile browser + installable) | Planned — **no native apps** |
| **6** | Analytics, eval gates, cost dashboards | Planned |

Full index: [docs/phases.md](docs/phases.md)  
Phase 0: [retro](docs/retrospectives/phase-0.md) · [report](docs/reports/phase-0-engineering-report.md)  
Phase 1: [retro](docs/retrospectives/phase-1.md) · [report](docs/reports/phase-1-engineering-report.md)  
Phase 2: [retro](docs/retrospectives/phase-2.md) · [report](docs/reports/phase-2-engineering-report.md)

### Phase 2 MVP lifecycle (API)

```text
POST /api/v1/documents/upload
POST /api/v1/documents/{id}/versions/{vid}/publish
POST /api/v1/documents/{id}/versions/{vid}/retire
```

Runbooks: [upload](docs/runbooks/document-upload-api.md) · [lifecycle](docs/runbooks/version-lifecycle.md)

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
| [docs/adr/](docs/adr/) | Architecture Decision Records (0001–0006) |
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
# set GCP_PROJECT_ID and other local values — never commit .env
```

### Terraform (multi-env — Phase 1.1)

Layout: `terraform/` with `environments/{dev,test,prod}/` (`terraform.tfvars` + `backend.hcl`).

```bash
cd terraform
# After bootstrap (state already in gs://enterprise-rag-tfstate-dev):
terraform init -reconfigure -backend-config=environments/dev/backend.hcl
terraform plan  -var-file=environments/dev/terraform.tfvars
# terraform apply -var-file=environments/dev/terraform.tfvars
```

State buckets: `enterprise-rag-tfstate-dev|test|prod` (versioning + uniform access + soft-delete).  
Full bootstrap / migrate steps: [docs/runbooks/terraform-bootstrap.md](docs/runbooks/terraform-bootstrap.md)

---

## Security highlights

- **Zero JSON service-account keys** — forever; CI uses GitHub OIDC + WIF only  
  - SAs: `sa-rag-api`, `sa-rag-ingest`, `sa-rag-web`, `sa-rag-ci`  
  - Pool: `rag-github-pool` · Provider: `github-oidc`  
  - Runbook: [docs/runbooks/github-actions-wif.md](docs/runbooks/github-actions-wif.md)  
  - ADR: [docs/adr/0005-security-posture.md](docs/adr/0005-security-posture.md)
- Secrets in **Secret Manager** only; `.env` gitignored
- Least-privilege **custom SAs** (CI vs runtime); tighten storage.admin on CI later
- **CMEK:** `rag-keyring` / `rag-secrets-key` (secrets) + `rag-gcs-key` (docs buckets) — [secrets](docs/runbooks/secret-manager-cmek.md) · [docs buckets](docs/runbooks/gcs-document-buckets.md)
- **Document storage:** `rag-docs-{dev,test,prod}` with prefixes `raw/`, `versions/`, `assets/`, `processed/`
- Non-root containers (uid/gid **1001**)
- No PII in logs/analytics by default (hashed subject IDs)
- Auth domain allowlist: `chandraailabs.com`, `gmail.com`

---

## CI / CD

- Workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)  
- Runbook: [docs/runbooks/github-actions-ci.md](docs/runbooks/github-actions-ci.md)  
- **Keyless only:** WIF provider  
  `projects/642114828076/locations/global/workloadIdentityPools/rag-github-pool/providers/github-oidc`  
- Artifact Registry: `asia-south1-docker.pkg.dev/enterprise-rag-platform-502711/rag-containers`  
- Deploy target on `main` push: Cloud Run **`rag-api`**

```text
![CI](https://github.com/chandranakkalakunta/enterprise-rag-platform/actions/workflows/ci.yml/badge.svg)
```

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
