# Changelog

All notable changes to this project are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Phases map to project delivery, not strictly SemVer until first production release.

---

## [Unreleased]

### Planned
- Phase 1: GCP API enablement, CMEK, auth allowlist, WIF CI, health version fields in code, three Cloud Run services

### Added
- Phase 0 Gamma requirements lock (`docs/requirements.md` v3): audience (`chandraailabs.com` + `gmail.com`), 5-star feedback, metadata filtering, semantic caching, multimodal (tables/images), health `version`+`deployed_at`, zero JSON keys / WIF / defence-in-depth, synthetic+OSS data note
- UI specs: StarRating, multimodal rendering, non-blocking feedback
- Architecture: Cloud Run `api` + `ingest-worker` + `web`, LangGraph path, cache/filter/multimodal
- ADR-0005 security posture; ADR-0002 amended (LangGraph, Vertex AI Vector Search locked, multimodal)
- Phase 0 Beta documentation: requirements v2, ui-specs, architecture overview, ADR-0003/0004, shadcn/ui

### Fixed
- Removed hard-coded GCP project ID from docs and Terraform; use `var.gcp_project_id` / placeholder `your-gcp-project-id` (Phase 0.1)

---

## [0.1.0] — 2026-07-16 — Phase 0: Project Foundation

### Added
- Git repository initialized on branch `phase-0-initialization`
- Monorepo structure: `backend/`, `frontend/`, `terraform/`, `docs/`, `scripts/`, `config/`
- `docs/requirements.md` — personas, user stories, NFRs, success criteria
- `docs/adr/0000-adr-template.md` — project ADR template
- `docs/adr/0001-high-level-architecture.md` — system architecture (Accepted)
- `docs/adr/0002-tech-stack.md` — stack & toolchain (Accepted)
- `docs/backlog.md` — living backlog with domain groups
- `docs/grok-three-agent-protocol.md` — Grok-adapted Three-Agent Protocol v1.0
- Terraform skeleton (`providers.tf`, `variables.tf`, `main.tf`, dev tfvars example) parameterized via `var.gcp_project_id`
- FastAPI placeholder API with `/health`, `/ready`, OpenAPI
- Backend `requirements.txt` (pinned) + `pyproject.toml` + pytest smoke tests
- Next.js 15 + TypeScript frontend placeholder (`package.json`, App Router page)
- Root `.gitignore`, `.env.example`, `README.md`

### Security
- Established conventions: no secrets in git, Secret Manager for deploy, `.env` ignored
