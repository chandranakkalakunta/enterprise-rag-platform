# Changelog

All notable changes to this project are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Phases map to project delivery, not strictly SemVer until first production release.

---

## [Unreleased]

### Planned
- Phase 1: GCP API enablement, CMEK, auth, CI foundation

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
