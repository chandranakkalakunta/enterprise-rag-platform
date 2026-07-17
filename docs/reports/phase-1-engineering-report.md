# Phase 1 Engineering Report — GCP Foundation

**Project:** Enterprise RAG Platform  
**GCP project:** `enterprise-rag-platform-502711` (number `642114828076`)  
**Phase:** 1 — GCP Foundation  
**Date:** 2026-07-17  
**PR range:** [#3](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/3)–[#9](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/9)  
**Status:** **Complete** — ready for Phase 2  

Related: [Phase 1 retrospective](../retrospectives/phase-1.md)

---

## 1. Deliverables

| Area | Deliverable | PR | Verified live |
|------|-------------|-----|---------------|
| IaC multi-env | Terraform `dev`/`test`/`prod` + remote state | #3 | Yes |
| APIs | Minimum required Google APIs only | #3 | Yes |
| State | `enterprise-rag-tfstate-{dev,test,prod}` | #3 | Yes |
| Identity | `sa-rag-api`, `sa-rag-ingest`, `sa-rag-web`, `sa-rag-ci` | #4 | Yes |
| WIF | Pool `rag-github-pool`, provider `github-oidc`, repo-restricted | #4 | Yes |
| CMEK | `rag-keyring` / `rag-gcs-key` / `rag-secrets-key` (90-day rotation) | #5 | Yes |
| Secrets | `rag-oauth-client-id`, `rag-oauth-client-secret` (empty shells, CMEK) | #5 | Yes |
| Docs storage | `rag-docs-{dev,test,prod}` + CMEK + lifecycle + bucket IAM | #6 | Yes |
| Health | `/health`, `/ready` with `version` + `deployed_at` | #7 | Yes |
| IAM tighten | Project `storage.admin` removed from CI SA | #7 | Yes |
| Compute stubs | Cloud Run `rag-api`, `rag-ingest`, `rag-web` | #8 | Yes |
| CI/CD | GHA test → build → deploy via WIF to `rag-api` | #9 | Yes |

---

## 2. Key decisions locked

| Decision | Choice |
|----------|--------|
| Auth to GCP for automation | **WIF + OIDC only** — zero JSON SA keys |
| CI identity | `sa-rag-ci@…` (deploy only) |
| Runtime identities | Separate SAs for api / ingest / web |
| Encryption | CMEK for secrets and document GCS; separate keys |
| State | Per-env GCS state buckets; foundation state in dev backend |
| Document layout | Prefixes `raw/`, `versions/`, `assets/`, `processed/` |
| Health contract | `APP_VERSION` + `DEPLOYED_AT` env injection |
| Audience (auth later) | `chandraailabs.com` + `gmail.com` allowlist |
| Binary Authorization | Deferred to Phase 6+ (NFR-SEC-14 / BL-SEC-09) |

---

## 3. Architecture snapshot (post–Phase 1)

```text
GitHub Actions (OIDC)
        │ WIF
        ▼
   sa-rag-ci ──build/push──▶ Artifact Registry (rag-containers)
        │ deploy
        ▼
   Cloud Run: rag-api (sa-rag-api) · rag-ingest · rag-web
        │
        ├── Secret Manager (CMEK: rag-secrets-key)
        ├── GCS rag-docs-* (CMEK: rag-gcs-key)
        └── KMS rag-keyring (asia-south1)
```

---

## 4. Residual risks (not Phase 1 blockers)

| Risk | Tracking | Mitigation path |
|------|----------|-----------------|
| Binary Authorization not enforced | BL-SEC-09 / BL-FND-26 | Phase 6+ hardening |
| `rag-web` / `rag-ingest` still on placeholder images | Phase 2+ CI jobs | Extend pipeline per service |
| OAuth secret values empty | Coordinator | [secret-manager-cmek.md](../runbooks/secret-manager-cmek.md) |
| detect-secrets not in CI | BL-FND-08 | Early Phase 2 |
| No prefix-level GCS IAM conditions | Future | Optional hardening |
| Public invoker not enabled on rag-api | Intentional | Auth layer / invoker IAM in Phase 2 |

---

## 5. Readiness for Phase 2

**Green.** Foundation is production-grade for building ingestion:

1. Write objects into `gs://rag-docs-dev` under the prefix convention.  
2. Implement versioning state machine (ADR-0003) on ingest path.  
3. Wire real `rag-ingest` image via CI when ready.  
4. Keep WIF for all automation; never introduce JSON SA keys.

---

## 6. Sign-off

Phase 1 (GCP Foundation) is **complete**.  
**Next:** Phase 2 — Ingestion Foundation.
