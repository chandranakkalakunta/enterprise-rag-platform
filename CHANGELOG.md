# Changelog

All notable changes to this project are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Phases map to project delivery, not strictly SemVer until first production release.

---

## [Unreleased]

### Planned
- Phase 1.4+: auth allowlist, health `version` + `deployed_at` in code, Cloud Run services, Binary Authorization
- Coordinator: add OAuth secret versions (shells exist)

### Added
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

### Changed
- Phase 0.1 hotfix: GCP project example/default switched to `enterprise-rag-platform-502711` (project number `642114828076`) via `var.gcp_project_id` / `GCP_PROJECT_ID` — no application hard-coding; old placeholder/dev IDs removed from examples

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

### Fixed
- Removed hard-coded GCP project IDs; use `var.gcp_project_id` / placeholder only (Phase 0.1)

### Security
- Conventions locked: no secrets in git, zero JSON SA keys, Secret Manager for deploy, defence-in-depth (ADR-0005)
