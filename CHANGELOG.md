# Changelog

All notable changes to this project are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Phases map to project delivery, not strictly SemVer until first production release.

---

## [Unreleased]

### Planned
- Phase 1: GCP API enablement, CMEK, auth allowlist, WIF CI, health `version` + `deployed_at` in code, three Cloud Run services

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
