# ADR-0009: AuthN / AuthZ and User Profiles (Firestore)

## Status

Accepted — 2026-07-19

## Context

Phase 5 delivers the full PWA/UI that calls backend APIs for upload, publish/retire, search, and grounded answers. Today those APIs still use temporary Bearer / `AUTH_DEV_BYPASS` gates (Phase 2 residual). Product and security requirements already lock:

- **Google OAuth** and domain allowlist (`chandraailabs.com`, `gmail.com`) — [ADR-0005](./0005-security-posture.md), [requirements](../requirements.md)  
- Role model for content administration vs end users  
- **No anonymous UI** for this product (authenticated access only)  

We need a durable, backend-enforced identity and role store before Phase 5.1 wires real login.

Forces:

1. Backend must be **source of truth** for authorization (never trust client-only role flags)  
2. Small team needs **bootstrap admins** without a separate admin-provisioning UI on day one  
3. User profile and role data should fit existing **Firestore Native** metadata ([ADR-0006](./0006-metadata-store-firestore.md))  
4. Align with existing OAuth secret shells (`rag-oauth-client-id` / `rag-oauth-client-secret`)  

## Decision

### Authentication (AuthN)

| Item | Choice |
|------|--------|
| Provider | **Google OAuth 2.0 / Sign in with Google** |
| Allowed email domains | **`chandraailabs.com`**, **`gmail.com`** |
| Anonymous / guest UI | **Not allowed** — unauthenticated users see login (and domain-denied) only |
| Session | Server-validated token/session (implementation in Phase 5.1+); details may use ID token verification + session cookie or API Bearer of Google ID token |

Domain check is enforced on **first login and every authenticated request** (not only at account create).

### Authorization (AuthZ)

| Item | Choice |
|------|--------|
| Model | RBAC: **`viewer`** \| **`content_admin`** \| **`admin`** |
| Enforcement | **Backend only** — every protected route checks identity + role |
| UI | Reflects roles from **`GET /api/v1/me`** (or equivalent); must not authorize by client-side flags alone |

**Role capabilities (MVP guidance):**

| Role | Intended access |
|------|-----------------|
| `viewer` | Query search/answer; read own profile; no upload/publish/retire admin mutations |
| `content_admin` | Viewer + document upload, publish, retire, admin document APIs |
| `admin` | Content admin + future operator/settings; bootstrap super-user |

(Exact route map implemented in Phase 5.x; this ADR locks the role vocabulary and enforcement principle.)

### User profile store

Profiles and roles live in **Firestore**:

```text
users/{uid}
```

**Minimum fields:**

| Field | Type / notes |
|-------|----------------|
| `email` | string (verified Google email) |
| `display_name` | string |
| `photo_url` | string \| null |
| `role` | `viewer` \| `content_admin` \| `admin` |
| `created_at` | timestamp |
| `last_login_at` | timestamp |

Optional later: `disabled`, hashed subject for analytics, ACL labels.

### Bootstrap elevated roles

Config-driven allowlists (env / Secret Manager; never hard-code in frontend):

| Variable | Purpose |
|----------|---------|
| **`ADMIN_EMAILS`** | Comma-separated emails → role `admin` on first login (and re-assert on login if still listed) |
| **`CONTENT_ADMIN_EMAILS`** (optional) | Comma-separated emails → role `content_admin` if not already admin |

**Default** for any other allowlisted-domain user: **`viewer`**.

Bootstrap lists are the **only** automated elevation path for MVP. Role demotion/promotion UI is later.

### Identity API for the frontend

- **`GET /api/v1/me`** (Phase 5.1+) returns authenticated user: email, display name, photo, **role**, uid.  
- Frontend uses this for nav/gates (show Admin link only if role allows) **and** all mutations still require backend authz.

### Relationship to temporary auth

Phase 2–3 `AUTH_DEV_BYPASS` / shared Bearer remain **dev-only** until OAuth is wired; production Phase 5 path replaces them for user-facing routes (BL-SEC-10).

## Rationale

| Criterion | Why |
|-----------|-----|
| Google OAuth | Matches locked audience (Gmail + workspace domain); no password store |
| Domain allowlist | Product non-negotiable; reduces open internet abuse |
| Firestore `users/{uid}` | Same metadata store as documents; serverless; least new infra |
| Backend enforcement | Prevents privilege escalation via UI tampering |
| Config bootstrap emails | Fast ops for Chandra AI Labs without day-one user-admin UI |

## Consequences

### Positive

- Clear AuthN/AuthZ contract for Phase 5.1 implementation  
- Roles portable across api routes (upload, lifecycle, query)  
- Aligns secrets already provisioned for OAuth  

### Negative / Trade-offs

- Gmail allowlist is broad (any gmail.com account can become viewer if they can open the app URL) — mitigated by private URL + later tighter controls if needed  
- Bootstrap email lists require careful Secret Manager handling  
- Role renames later need migration of Firestore docs  

### Risks and Mitigations

- **Risk:** Client trusts a forged role in localStorage  
  - **Mitigation:** Backend rejects unauthorized mutations; UI only hides controls  
- **Risk:** Bootstrap email typo locks out admins  
  - **Mitigation:** Document dual-admin emails; Coordinator runbook for `ADMIN_EMAILS`  
- **Risk:** Domain spoofing  
  - **Mitigation:** Verify Google token `email_verified` and hd/email domain server-side  

## Alternatives Rejected

### Client-only roles (role in JWT payload without server profile)

- Why rejected: Trivial to spoof or desync; violates backend source-of-truth.

### Hard-coded user list or roles in the frontend bundle

- Why rejected: Secrets and allowlists leak; no server enforcement.

### Custom username/password IdP

- Why rejected: Higher ops and security burden; Google OAuth already locked.

### External IdP-only groups without Firestore profile

- Why rejected: Still need profile + last_login for product UX; Firestore is already the metadata plane.

## References

- [ADR-0005 Security Posture](./0005-security-posture.md)  
- [ADR-0006 Metadata Store — Firestore](./0006-metadata-store-firestore.md)  
- [ADR-0010 PWA Frontend Shell and Version Auto-Reload](./0010-pwa-shell-version-reload.md)  
- [requirements.md](../requirements.md) (audience, roles)  
- [ui-specs.md](../ui-specs.md) (domain-denied login)  
- [oauth-domain-allowlist.md](../runbooks/oauth-domain-allowlist.md)  
- Backlog: BL-SEC-01, BL-SEC-02, BL-SEC-10, BL-FE-09  
