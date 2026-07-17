# Runbook: OAuth domain allowlist (prep — Phase 1.6)

**Status:** Specification only in Phase 1.6 — application enforcement lands with auth implementation (BL-SEC-01).  
**Requirement:** NFR-SEC-13 · US-AUTH-01 · US-EU-01  

## Allowed email domains

| Domain | Purpose |
|--------|---------|
| `chandraailabs.com` | Primary org identities |
| `gmail.com` | Collaborators / demos |

**All other domains:** deny after Google OAuth completes (clear error; no partial session).

## Implementation notes (for later code)

1. Complete Google OAuth / Identity Platform sign-in.  
2. Read verified email from ID token claims.  
3. Extract domain (`email.split("@")[-1].lower()`).  
4. Allow only if domain ∈ configured allowlist.  
5. Allowlist source: config / Secret Manager (not hard-coded secrets).  
6. Log deny events with **hashed** subject id only (no raw email in analytics).

## Secrets (shells exist — Phase 1.3)

| Secret ID | Purpose |
|-----------|---------|
| `rag-oauth-client-id` | OAuth client ID (CMEK) |
| `rag-oauth-client-secret` | OAuth client secret (CMEK) |

Coordinator adds versions via [secret-manager-cmek.md](./secret-manager-cmek.md).

## Related

- Cloud Run stubs: `rag-api`, `rag-ingest`, `rag-web` (Phase 1.6) — real auth on `rag-api` later  
- ADR-0005 Security Posture  
