# ADR-0010: PWA Frontend Shell and Backend Version Auto-Reload

## Status

Accepted — 2026-07-19

## Context

Phase 5 builds the production-facing UI for the Enterprise RAG Platform. Constraints already locked:

- **Next.js** App Router, TypeScript, Tailwind, **shadcn/ui** — [ADR-0002](./0002-tech-stack.md), [ui-specs](../ui-specs.md)  
- **Full PWA** on desktop/tablet/mobile browsers; **no native app stores** — Phase 3/2 closures  
- Backend already exposes **`/health`** and **`/ready`** with `version` + `deployed_at` (Phase 1.5, NFR-REL-03a)  
- Cloud Run deploys new API images via CI; a service worker or long-lived tab can keep **stale frontend** talking to a **new API** (or the reverse)  

Forces:

1. Installable PWA shell must not block network-required RAG answers  
2. Deploy safety: UI must not silently break after API revision changes  
3. External **HTTPS Load Balancer + Cloud Armor** is desired for prod hardening but **not** required for Phase 5 MVP  

## Decision

### Frontend application

| Item | Choice |
|------|--------|
| Location | **`frontend/`** monorepo package |
| Framework | **Next.js 15** App Router + TypeScript |
| UI | **Tailwind CSS** + **shadcn/ui** + Lucide (per ui-specs) |
| API base | **`NEXT_PUBLIC_API_BASE_URL`** (env; no hard-coded project URLs in source beyond examples) |
| Auth UX | Google sign-in; domain allowlist; roles from backend `/api/v1/me` — [ADR-0009](./0009-authn-authz-user-profiles.md) |

### Delivery profile (PWA)

| In scope | Out of scope |
|----------|--------------|
| Responsive web: **desktop, tablet, mobile browsers** | Native iOS App Store apps |
| **Installable PWA** (web app manifest + service worker for shell) | Native Android Play Store apps |
| Offline: **app shell only** | Offline RAG answers or offline document admin |
| Online chat/search/answer via API | Separate native codebases |

Answers, upload, and admin mutations **require network**. Offline shell may show a banner and disable send/mutations.

### Backend version auto-reload (mandatory)

Backend continues to expose on **`/health`** and **`/ready`**:

```json
{
  "status": "ok",
  "service": "rag-api",
  "version": "<APP_VERSION>",
  "deployed_at": "<DEPLOYED_AT ISO-8601>"
}
```

**Frontend SHALL:**

1. On app load, fetch health (or ready) and store last-seen `version` and `deployed_at` (memory + durable storage as needed).  
2. **Poll** health on a fixed interval (implementation default e.g. 30–60s; configurable).  
3. Also re-check on **window focus** and **document visibility** (`visibilitychange`).  
4. If **either** `version` **or** `deployed_at` **changes** relative to last seen → **force a full page reload** (`location.reload()` or equivalent hard navigation).  

**Purpose:** Avoid stale PWA/UI shells and cached JS talking to an incompatible API after Cloud Run deploy (and avoid half-migrated client state).

**Non-goals for this control:** Feature-flag negotiation, graceful schema migration UI, or soft prompts only — Phase 5 requires **hard reload** on version change.

### Load balancer / Cloud Armor (future note)

| Item | Decision |
|------|----------|
| Phase 5 | Clients may call **Cloud Run service URLs** (or simple mapping) via `NEXT_PUBLIC_API_BASE_URL` |
| Future (Phase 6+ / pre-prod hardening) | **HTTPS Load Balancing + Cloud Armor** in front of Cloud Run (and optionally web) — rate limits, WAF, custom domain, TLS  

LB/Armor is **not** a Phase 5.0/5.1 gate; document only so architecture stays intentional ([BL-FND-16](../backlog.md)).

## Rationale

| Criterion | Why |
|-----------|-----|
| Next.js + shadcn | Already locked stack and ui-specs |
| Installable PWA, no native | Product and Phase 5 scope lock |
| Health-based reload | Uses existing deploy metadata; zero new backend contract fields |
| Shell-only offline | RAG needs live API + Vertex; offline answers would be misleading |
| Defer LB | Cost and complexity; Cloud Run HTTPS sufficient for early Phase 5 |

## Consequences

### Positive

- Clear frontend package and API config contract  
- Safer continuous deploy against long-lived browser sessions / installed PWAs  
- Aligns offline expectations with product honesty  

### Negative / Trade-offs

- Hard reload can interrupt in-progress chat draft (acceptable; prefer correctness)  
- Polling adds minor health traffic (interval tunable)  
- Without LB, DDoS/WAF controls are limited until Phase 6+  

### Risks and Mitigations

- **Risk:** Health poll fails transiently and triggers false reload  
  - **Mitigation:** Reload only when a **successful** health response shows a **changed** version/deployed_at; ignore network errors  
- **Risk:** Service worker serves stale shell forever  
  - **Mitigation:** Version reload + SW update strategy on app load (Phase 5.1 implementation)  
- **Risk:** CORS / cookie issues across API and web origins  
  - **Mitigation:** Explicit CORS allowlist and auth cookie design in Phase 5.1  

## Alternatives Rejected

### Soft “please refresh” toast without forced reload

- Why rejected: Users ignore toasts; stale clients continue to break.

### Build-id only in frontend env without polling backend

- Why rejected: Does not detect API-only deploys that change contracts.

### Native store apps alongside PWA

- Why rejected: Explicitly out of scope for this product track.

### Mandatory Cloud Armor / global LB in Phase 5

- Why rejected: Not required for functional PWA MVP; scheduled as future hardening.

## References

- [ADR-0002 Tech Stack](./0002-tech-stack.md)  
- [ADR-0005 Security Posture](./0005-security-posture.md)  
- [ADR-0009 AuthN/AuthZ and User Profiles](./0009-authn-authz-user-profiles.md)  
- [ui-specs.md](../ui-specs.md) (§7 PWA)  
- [requirements.md](../requirements.md) (PWA / install stories)  
- Health contract: Phase 1.5 / NFR-REL-03a  
- Backlog: BL-PWA-01–03, BL-FE-01–05, BL-FND-16 (LB + Armor)  
