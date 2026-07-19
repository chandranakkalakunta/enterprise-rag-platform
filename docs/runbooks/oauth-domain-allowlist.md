# Runbook: OAuth domain allowlist (prep — Phase 1.6)

**Status:** Spec from Phase 1.6 — **enforced in Phase 5.1** (see [oauth-and-frontend-auth.md](./oauth-and-frontend-auth.md)).  
**Requirement:** NFR-SEC-13 · US-AUTH-01 · US-EU-01  

## Allowed email domains

| Domain | Purpose |
|--------|---------|
| `chandraailabs.com` | Primary org identities |
| `gmail.com` | Collaborators / demos |

**All other domains:** deny after Google OAuth completes (clear error; no partial session).

## Implementation notes (Phase 5.1)

1. Google Identity Services → ID token → API `Authorization: Bearer`.  
2. Backend verifies token (`email_verified`, audience = OAuth client id).  
3. Extract domain (`email.rsplit("@", 1)[-1].lower()`).  
4. Allow only if domain ∈ `ALLOWED_EMAIL_DOMAINS`.  
5. Allowlist source: env config (not hard-coded secrets).  
6. Log deny events with domain only / hashed uid (no raw email in analytics logs).

## Secrets (shells exist — Phase 1.3)

| Secret ID | Purpose |
|-----------|---------|
| `rag-oauth-client-id` | OAuth client ID (CMEK) |
| `rag-oauth-client-secret` | OAuth client secret (CMEK) |

Coordinator adds versions via [secret-manager-cmek.md](./secret-manager-cmek.md).

## Related

- Cloud Run stubs: `rag-api`, `rag-ingest`, `rag-web` (Phase 1.6) — real auth on `rag-api` later  
- ADR-0005 Security Posture  
