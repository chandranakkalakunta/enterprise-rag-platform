# ADR-0012: Production Edge Access — HTTPS LB + IAP in Front of Cloud Run

## Status

Accepted — 2026-07-21

## Context

The product needs **browser access end-to-end on Cloud Run** without developers running local `uvicorn` / proxy shims. Org policy **blocks `allUsers` (and public) `roles/run.invoker`** on Cloud Run — Coordinator decision: **no exceptions**.

Forces:

1. **No public Cloud Run invoker** — internet must not call `*.run.app` as unauthenticated invokers  
2. **Production-grade browser path** — HTTPS, Google identity at the edge, least privilege  
3. **Same-origin preferred** for the PWA (cookies/CORS simpler; path routing UI + API)  
4. **App authorization** remains Firestore RBAC (`viewer` / `content_admin` / `admin`) per [ADR-0009](./0009-authn-authz-user-profiles.md)  
5. Phase 5 GIS “Bearer Google ID token” path works for early demos; edge IAP is the **production** AuthN boundary  
6. [ADR-0010](./0010-pwa-shell-version-reload.md) deferred LB/Armor to Phase 6+ — that time is now for edge design  

## Decision

### Edge pattern

| Item | Choice |
|------|--------|
| Edge | **Global external HTTPS Application Load Balancer** |
| Identity at edge | **Identity-Aware Proxy (IAP)** on backend services |
| Backend | **Serverless NEGs** → Cloud Run `rag-web` and `rag-api` |
| Cloud Run invoker | **Not** `allUsers` / `allAuthenticatedUsers` as public internet invoker |
| Cloud Run ingress | **`internal-and-cloud-load-balancing`** (only LB can reach services) |
| Browser origin | **Prefer single host**, path-based routing |
| Dual-host alternative | Documented fallback (UI host + API host) if path routing is blocked by app constraints |

### Path routing (preferred)

Single public hostname (LB IP / custom domain later), for example:

| Path | Backend |
|------|---------|
| `/` , `/_next/*`, PWA assets, app routes | `rag-web` (Next.js) |
| `/api/*`, `/health`, `/ready`, `/docs` (if exposed) | `rag-api` (FastAPI) |

Frontend `NEXT_PUBLIC_API_BASE_URL` becomes **same origin** (e.g. empty base or `https://app.example.com`) so the browser only talks to the LB.

### Dual-host alternative (documented, not preferred)

| Host | Service |
|------|---------|
| `app.<domain>` | `rag-web` |
| `api.<domain>` | `rag-api` |

Requires CORS + OAuth client origins for both; more config surface. Use only if path routing proves impractical.

### Authentication & authorization

| Layer | Responsibility |
|-------|----------------|
| **IAP** | Authenticate human users (Google identity) before traffic reaches Cloud Run |
| **Cloud Run** | Accept only LB traffic; invoker granted to **IAP / LB service agents**, not public |
| **App AuthZ** | Unchanged: roles in Firestore `users/{uid}`; mutations enforced on API |
| **App AuthN (preferred, Phase 6.2)** | Validate **IAP JWT** (`X-Goog-IAP-JWT-Assertion`) on `rag-api` (and optionally trust identity on `rag-web` BFF later) → map email/sub → domain allowlist → upsert `/me` |
| **Fallback (transition)** | Existing GIS Google ID token Bearer ([ADR-0009](./0009-authn-authz-user-profiles.md)) until 6.2 ships; do **not** use public invoker to enable that path in prod |

Domain allowlist (`chandraailabs.com`, `gmail.com`) remains enforced in app (and IAP access list should only grant intended principals / groups).

### Custom domain & TLS

| Stage | Choice |
|-------|--------|
| 6.1 bootstrap | LB with **Google-managed cert** when domain is available; until then, access via **LB IP + host header** or temporary managed cert on a provisional hostname if org DNS allows |
| Later | Custom domain (e.g. `rag.chandraailabs.com`) + managed SSL certificate resource |

### Cloud Armor

**Out of scope for 6.0 decision core**; track as optional hardening after LB/IAP works (still under Phase 6 / BL-FND-16 residual). IAP is the primary “no anonymous internet” control.

### Terraform resource list (Phase 6.1 implementation target)

Implement in `terraform/` (env-aware, no hard-coded project IDs in modules):

| Resource | Purpose |
|----------|---------|
| `google_compute_global_address` | Global anycast IP for HTTPS |
| `google_compute_region_network_endpoint_group` (SERVERLESS) ×2 | NEGs for `rag-web`, `rag-api` |
| `google_compute_backend_service` ×2 | Backends; **IAP enabled** on each (or as required for path split) |
| IAP OAuth brand / client (or use project-level IAP config) | IAP sign-in |
| `google_compute_url_map` | Path rules: UI vs API |
| `google_compute_target_https_proxy` | HTTPS termination |
| `google_compute_global_forwarding_rule` | 443 → HTTPS proxy |
| `google_compute_managed_ssl_certificate` (when domain ready) | Managed cert |
| Optional HTTP→HTTPS redirect URL map + proxy | Force TLS |
| Cloud Run service settings | `ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"` (or `internal-and-cloud-load-balancing`) |
| IAM | **IAP service agent** → `roles/run.invoker` on `rag-web` + `rag-api` |
| IAM | Allowed principals → `roles/iap.httpsResourceAccessor` on IAP-protected backends |
| **Forbidden** | `allUsers` / public `run.invoker` on application services |

### Implementation phasing

| Step | Scope |
|------|--------|
| **6.0** | This ADR (Accepted) + living docs |
| **6.1** | Terraform LB + serverless NEG + IAP + ingress lock; smoke HTTPS via LB |
| **6.2** | App: prefer IAP JWT identity → `/me` / protected routes; frontend same-origin base URL; retire public GIS-only reliance for prod |
| **Later** | Custom domain polish; Cloud Armor policies; Binary Auth (separate track) |

### Security non-negotiables

- **No anonymous internet to Cloud Run** invoker  
- Ingress restricted to load balancer  
- Secrets remain in Secret Manager (CMEK)  
- Least-privilege service accounts (existing ADR-0005)  

## Rationale

| Criterion | Why |
|-----------|-----|
| LB + serverless NEG | Supported pattern for Cloud Run behind global HTTPS without public invoker |
| IAP | Org-friendly Google sign-in at edge; fits “no allUsers” policy |
| Path routing | One origin for PWA + API reduces CORS and cookie complexity |
| IAP JWT in app (6.2) | Avoid double-login UX long-term; still keep Firestore roles as AuthZ source of truth |
| Ingress restriction | Defense in depth if run URL is guessed |

## Consequences

### Positive

- Production browser access without violating org invoker policy  
- Clear Terraform backlog for 6.1  
- Aligns with zero-trust style edge AuthN  

### Negative / Trade-offs

- IAP + LB operational complexity (OAuth brand, accessors, cert DNS)  
- Path routing must exclude Next.js routes that collide with `/api` (app already uses `/api/v1` on backend; Next may use `/api` only if introduced carefully)  
- Cold-start / multi-hop latency vs direct Cloud Run URL  

### Risks and Mitigations

- **Risk:** Health checks / LB require invoker-compatible access  
  - **Mitigation:** Use documented Cloud Run + serverless NEG health settings; grant only service agents  
- **Risk:** Double AuthN (IAP + GIS) confuses users  
  - **Mitigation:** 6.2 prefers IAP identity; document transition  
- **Risk:** Path split breaks Next asset routes  
  - **Mitigation:** Default route → web; only explicit API prefixes → api  
- **Risk:** IAP accessor list too broad (any Google account)  
  - **Mitigation:** Restrict to Workspace group / listed users; keep app domain allowlist  

## Alternatives Rejected

### `allUsers` run.invoker on Cloud Run

- Why rejected: Org policy + Coordinator decision; security non-negotiable.

### Public Cloud Run + only app-layer Google OAuth

- Why rejected: Still requires public invoker for browser→API; fails org policy.

### VPC-only / Identity-Aware internal without external LB

- Why rejected: Product needs external browser users (allowlisted), not only corporate VPC.

### API Gateway / Cloud Endpoints only for API

- Why rejected: Still need UI hosting and unified browser story; LB+IAP covers both services consistently.

## References

- [ADR-0005 Security Posture](./0005-security-posture.md)  
- [ADR-0009 AuthN/AuthZ](./0009-authn-authz-user-profiles.md)  
- [ADR-0010 PWA + version reload](./0010-pwa-shell-version-reload.md) (LB deferred note)  
- GCP: External Application Load Balancer + serverless NEG + Cloud Run  
- GCP: Identity-Aware Proxy for HTTP(S) load balancers  
- Backlog: BL-FND-16, BL-SEC-13 (edge)  
