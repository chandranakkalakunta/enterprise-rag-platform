# Changelog

All notable changes to this project are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Phases map to project delivery, not strictly SemVer until first production release.

---

## [Unreleased]

### Planned
- Phase 2.1+: Ingestion foundation (upload, parse, versioning state machine, Firestore models)
- Coordinator: add OAuth secret versions (shells exist)
- Binary Authorization implementation (NFR-SEC-14 / BL-SEC-09) — Phase 6+
- detect-secrets in CI (BL-FND-08)

### Added
- **Phase 2.0:** [ADR-0006](docs/adr/0006-metadata-store-firestore.md) — Firestore (Native mode) accepted as long-term metadata store (documents, versions, ingest jobs); analytics remain on BigQuery

---

## [1.0.0] — 2026-07-17 — Phase 1: GCP Foundation (**Complete**)

**PR range:** [#3](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/3)–[#9](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/9)  
**Closure:** [Retrospective](docs/retrospectives/phase-1.md) · [Engineering report](docs/reports/phase-1-engineering-report.md)

### Summary
Production-grade keyless GCP foundation: multi-env Terraform, WIF CI, CMEK, document buckets, Cloud Run stubs, health contract, and GitHub Actions deploy to `rag-api`.

### Added
- **Phase 1.7:** GitHub Actions CI (test → build → deploy) via WIF; no JSON keys
- **Phase 1.7:** Artifact Registry `rag-containers` (asia-south1); `backend/Dockerfile` (Python 3.12, non-root 1001)
- **Phase 1.7:** Runbook `docs/runbooks/github-actions-ci.md`
- **Phase 1.6:** Cloud Run stubs `rag-api`, `rag-ingest`, `rag-web` with sa-rag-* SAs, scale-to-zero, `APP_VERSION`/`DEPLOYED_AT`
- **Phase 1.6:** NFR-SEC-14 Binary Authorization (future); BL-SEC-09 backlog; OAuth allowlist runbook
- **Phase 1.5:** `/health` and `/ready` return `status`, `service`, `version`, `deployed_at` from `APP_VERSION` / `DEPLOYED_AT`
- **Phase 1.5:** pytest coverage for health contract; `.env.example` documents deploy metadata env vars
- **Phase 1.4:** Application buckets `rag-docs-{dev,test,prod}` with CMEK `rag-gcs-key`, versioning, soft-delete 7d, 90-day non-current lifecycle, UBLA + public access prevention
- **Phase 1.4:** Bucket IAM for sa-rag-ingest / sa-rag-api / sa-rag-ci; Storage service agent KMS grant; runbook `docs/runbooks/gcs-document-buckets.md`
- **Phase 1.3:** KMS `rag-keyring` + `rag-gcs-key` / `rag-secrets-key` (90-day rotation, ENCRYPT_DECRYPT)
- **Phase 1.3:** Secret Manager shells `rag-oauth-client-id` / `rag-oauth-client-secret` with CMEK (no versions in TF)
- **Phase 1.3:** `cryptoKeyEncrypterDecrypter` for four SAs + Secret Manager service agent; runbook `docs/runbooks/secret-manager-cmek.md`
- **Phase 1.2:** Custom service accounts `sa-rag-api`, `sa-rag-ingest`, `sa-rag-web`, `sa-rag-ci`
- **Phase 1.2:** Workload Identity Pool `rag-github-pool` + GitHub OIDC provider `github-oidc` (repo-restricted)
- **Phase 1.2:** WIF binding `roles/iam.workloadIdentityUser` on `sa-rag-ci` for `chandranakkalakunta/enterprise-rag-platform`
- **Phase 1.2:** Baseline IAM (documented in `terraform/iam.tf`); runbook `docs/runbooks/github-actions-wif.md`
- **Phase 1.1:** Multi-env Terraform foundation (`dev` / `test` / `prod` tfvars + backend.hcl)
- Required Google APIs enabled via `google_project_service` (minimum set only)
- State buckets: `enterprise-rag-tfstate-dev`, `enterprise-rag-tfstate-test`, `enterprise-rag-tfstate-prod` (versioning, UBLA, soft-delete 7d, labels)
- Remote state migrated to `gs://enterprise-rag-tfstate-dev` (prefix `terraform/state`)
- Runbook: `docs/runbooks/terraform-bootstrap.md`
- Phase 1 retrospective and engineering report

### Changed
- **Phase 1.5:** Removed project-level `roles/storage.admin` from `sa-rag-ci` (bucket `objectAdmin` on `rag-docs-*` remains)
- Phase 0.1 hotfix: GCP project example/default switched to `enterprise-rag-platform-502711` (project number `642114828076`) via `var.gcp_project_id` / `GCP_PROJECT_ID`

---

## [0.1.0] — 2026-07-16 — Phase 0: Foundation & Requirements Lock (**Complete**)

**PR:** [#1](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/1) · **Branch:** `phase-0-initialization`  
**Closure:** [Retrospective](docs/retrospectives/phase-0.md) · [Engineering report](docs/reports/phase-0-engineering-report.md)

### Added
- Monorepo structure: `backend/`, `frontend/`, `terraform/`, `docs/`, `scripts/`, `config/`
- `docs/requirements.md` **v3.0** — personas, stories + acceptance criteria, NFRs, audience, multimodal, 5-star feedback, semantic cache, metadata filters, security
- `docs/ui-specs.md` — screens, PWA, voice, StarRating, multimodal, shadcn/ui
- `docs/architecture/overview.md` — LangGraph, three Cloud Run services, cache/filters/multimodal
- ADRs:
  - ADR-0001 high-level architecture
  - ADR-0002 tech stack (LangGraph, Vertex AI Vector Search, services)
  - ADR-0003 document versioning
  - ADR-0004 guardrails
  - ADR-0005 security posture (zero JSON keys, WIF/OIDC, defence-in-depth)
- Living backlog, Grok Three-Agent Protocol v1.0, issues log
- Terraform skeleton parameterized via `var.gcp_project_id`
- FastAPI + Next.js placeholders; pinned backend requirements; health smoke tests
- Phase 0 retrospective and engineering report
- `docs/phases.md` living phase index
- README status: Phase 0 complete

### Security
- Conventions locked: no secrets in git, zero JSON SA keys, Secret Manager for deploy, defence-in-depth (ADR-0005)
