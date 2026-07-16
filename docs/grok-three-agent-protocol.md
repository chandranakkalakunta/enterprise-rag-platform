# Grok Three-Agent Engineering Protocol — Project Adaptation v1.0

**Project:** Enterprise RAG Platform  
**Base protocol:** Chandra AI Labs Three-Agent Software Engineering Protocol (v3.8 lineage)  
**Adapted for:** Grok Build / single-orchestrator or multi-role sessions  
**Date:** 2026-07-16  

This document defines **HOW** we build this repository.  
Pair with `docs/requirements.md` for **WHAT** we build.

---

## 1. Roles

| Role | Responsibility |
|------|----------------|
| **Strategist** | Architecture, ADRs, sequencing, acceptance criteria, backlog hygiene, risk calls |
| **Worker** | Implementation, tests, commits on feature branches, CHANGELOG/backlog updates when instructed |
| **Coordinator (Human)** | Goals, priorities, approvals for destructive/shared-state actions, final product judgment |

In Grok Build sessions, one agent may wear Strategist + Worker hats sequentially, but **must not** skip Strategist design gates for architectural changes.

---

## 2. Non-Negotiables (from message one)

1. **Feature branches only** — never commit or push to `main` for feature work.
2. **Fail fast** — verify each step; do not stack unverified assumptions.
3. **Root cause over workaround** — default is the long-term fix; interim fixes must name the root cause, be labeled interim, and be logged in `docs/backlog.md`.
4. **ADRs for significant decisions** — use `docs/adr/0000-adr-template.md`.
5. **Living backlog** — deferrals go to `docs/backlog.md` immediately; completions note phase/PR.
6. **CHANGELOG** — update `CHANGELOG.md` for user-visible and foundation changes.
7. **No secrets in git** — Secret Manager only; `.env.example` committed, `.env` ignored.
8. **Pinned dependencies** — CI installs only from declared lock/requirements files.
9. **No PII in logs** — hash identifiers; structured JSON logging.
10. **Plan Mode** for complex, multi-path design before large code writes.
11. **Push / PR / shared systems** — confirm risk; never force-push to shared mainline.
12. **Coverage & quality gates** — measured baselines, not aspirational thresholds.

---

## 3. Branch & PR Workflow

```
main (protected)
  └── phase-N-<short-name>   # feature branch
        └── PR → main        # review + CI + merge
```

- One logical phase/PR theme per branch when practical.
- PR body: summary, test plan, risk notes, backlog/CHANGELOG pointers.
- Never push directly to `main`.

---

## 4. Phase Loop

1. **Align** — read requirements + relevant ADRs + backlog.
2. **Design** — Strategist produces plan/ADR deltas; Coordinator approves when architectural.
3. **Implement** — Worker executes on feature branch; small verifiable steps.
4. **Verify** — tests, smoke checks, structured pass/fail report.
5. **Document** — CHANGELOG, backlog, runbooks, README as needed.
6. **Integrate** — PR, review, merge; only then start next dependent phase.

**Sequencing vs scoping:** Do not start phase N+1 before N is validated when N may change unknowns. Within a phase, batch known work to minimize round-trips.

---

## 5. Documentation Standards

| Artifact | Path | Cadence |
|----------|------|---------|
| Requirements | `docs/requirements.md` | Update when scope changes |
| ADRs | `docs/adr/` | On each significant decision |
| Backlog | `docs/backlog.md` | Every deferral / completion |
| Changelog | `CHANGELOG.md` | Every PR set |
| Runbooks | `docs/runbooks/` | When ops procedures exist |
| Issues log | `docs/issues_log.md` | Every non-trivial problem + fix |
| Protocol | this file | Version bump on process change |

---

## 6. Risk Tiers (review intensity)

| Tier | Examples | Expectation |
|------|----------|-------------|
| **Low** | Docs, comments, pure refactors with tests | Lightweight review |
| **Medium** | API endpoints, UI flows, Terraform non-destructive | Tests + review |
| **High** | Auth, IAM, CMEK, data deletion, prod networking | Explicit design + dual check |
| **Critical** | Secret handling, public exposure, irreversible data loss | Coordinator approval before apply |

---

## 7. Verification Report Template (Worker)

After each phase/PR:

```markdown
## Verification Report
- Branch:
- Commit:
- Checks run:
- Pass / Fail table:
- Residual risks:
- Backlog updates:
- Next recommended step:
```

---

## 8. Token / Session Discipline (Grok)

- Batch independent shell checks; prefer structured verification lists.
- Confirm reproduction context before visual/functional diagnosis.
- Separate explanation (prose) from copy-paste command blocks when instructing humans.
- Do not re-derive architecture already locked in ADRs without new evidence.

---

## 9. Project-Specific Notes (Enterprise RAG)

- GCP project: `var.gcp_project_id` / `GCP_PROJECT_ID` (never hardcode project/region in app code or docs; use config/TF vars).
- Quality gates for retrieval/generation use **held-out** evaluation sets only.
- Hybrid retrieval + citations + version awareness are product pillars (see ADR-0001, ADR-0003).
- Guardrails are layered per ADR-0004; refuse when ungrounded.
- UI contract: `docs/ui-specs.md` (shadcn/ui); product contract: `docs/requirements.md`.
- Analytics: hashed IDs + metadata — no raw query text by default (NFR-PRV-01).

---

## 10. Changelog (this document)

| Version | Date | Notes |
|---------|------|-------|
| 1.0 | 2026-07-16 | Initial Grok-adapted protocol for enterprise-rag-platform Phase 0 |

---

## References

- Upstream: `Grok_ThreeAgent_Engineering_Protocol_v3_8.md` (Chandra AI Labs)
- `docs/requirements.md`
- `docs/adr/0001-high-level-architecture.md`
- `docs/adr/0002-tech-stack.md`
