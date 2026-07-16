# ADR-0005: Security Posture — Zero JSON Keys, WIF/OIDC, Defence-in-Depth

## Status

Accepted — 2026-07-16

## Context

The Enterprise RAG Platform handles document content, user identity, and LLM traffic on GCP. Common anti-patterns in GCP projects include:

- Downloading **JSON service-account keys** that leak via git, CI logs, or laptops  
- Over-privileged single SA used by all services  
- Relying on a single control (e.g. “private bucket”) without identity and application guardrails  

We must lock a security posture before Phase 1 CI/CD and Cloud Run wiring so that pipelines and runtime never depend on long-lived key files.

Audience allowlist (`chandraailabs.com`, `gmail.com`) and application guardrails (ADR-0004) complement infrastructure controls.

## Decision

### 1. Zero JSON service-account keys

- **Never** create, download, commit, mount, or base64-embed GCP service-account JSON key files for this project’s CI or runtime.  
- Local development uses **user Application Default Credentials** (`gcloud auth application-default login`) or impersonation where required.  
- CI/CD authenticates to GCP only via **Workload Identity Federation (WIF)** with OIDC tokens from the CI provider (e.g. GitHub Actions / Cloud Build).  
- Runtime on Cloud Run uses the **attached service account** metadata server (no key files in images or Secret Manager as “sa.json”).

### 2. Custom service accounts (least privilege)

Dedicated SAs (names illustrative; exact IDs via Terraform):

| Workload | SA purpose (minimum) |
|----------|----------------------|
| Cloud Run **api** | Invoke Vertex predict; read Secret Manager secrets it needs; read/write session/metadata as designed; publish analytics rows |
| Cloud Run **ingest-worker** | Read/write GCS version paths; write indexes; update job metadata |
| Cloud Run **web** | Serve frontend only; call **api** (no direct Vertex/GCS admin) |
| CI deploy | Deploy revisions, push Artifact Registry — not runtime data-plane admin |

Roles are discovered and tightened over time (least privilege is iterative) but **start deny-by-default**.

### 3. WIF + OIDC

- Prefer **OIDC federation** for any automation principal.  
- No long-lived JSON keys in GitHub secrets or Cloud Build substitutions.  
- Human break-glass uses IAM, not shared keys.

### 4. Defence-in-depth

Security is layered; no single control is sufficient:

| Layer | Controls |
|-------|----------|
| Identity | Google OAuth; email domain allowlist |
| AuthZ | RBAC + document ACL at retrieval |
| Application | Guardrails (ADR-0004); input size/rate limits |
| Secrets | Secret Manager; never in git |
| Data | CMEK on GCS (and eligible stores); hashed analytics subjects |
| Runtime | Non-root containers (uid 1001); minimal images |
| Network | Private where practical; **HTTPS LB + Cloud Armor later** (explicitly deferred) |
| Supply chain | Pinned deps; detect-secrets in CI when CI lands |

### 5. Health endpoints and information disclosure

`/health` and `/ready` expose `version` and `deployed_at` for operations. They **must not** expose secrets, SA emails beyond necessity, or internal connection strings.

## Rationale

- JSON SA keys are a leading cause of cloud credential incidents; WIF eliminates the class of failure.  
- Separate SAs limit blast radius across api / ingest / web.  
- Defence-in-depth matches enterprise expectations and prior production RAG practice.  
- Deferring LB/Armor is acceptable if services are correctly authenticated and not unnecessarily public with admin APIs open — still plan Armor before broad production exposure.

## Consequences

### Positive
- No key rotation theatre for SA JSON files  
- Clear CI story (WIF)  
- Auditable IAM per service  

### Negative
- Slightly more Terraform/IAM setup in Phase 1  
- Local dev requires gcloud auth discipline  

### Risks and Mitigations
- **Risk:** Someone generates a JSON key “just for a demo”  
  - **Mitigation:** Explicit forbid in protocol + detect-secrets + code review checklist  
- **Risk:** Over-permissive WIF attribute mapping  
  - **Mitigation:** Restrict repository/branch principals; review attribute conditions  

## Alternatives Rejected

### JSON keys in Secret Manager for Cloud Run
- Why rejected: Still long-lived keys; metadata SA is the platform-native pattern

### Single shared SA for all Cloud Run services
- Why rejected: Violates least privilege; ingest compromise would grant query-plane rights

### Defer all security until after feature complete
- Why rejected: Retrofitting WIF and SA splits is costly; lock now

## References

- [requirements.md](../requirements.md) — NFR-SEC-10…13, US-OPS-04  
- [ADR-0004 Guardrails](./0004-guardrails-architecture.md)  
- [architecture/overview.md](../architecture/overview.md)  
- Google Cloud WIF documentation  
