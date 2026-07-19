# Phase 5 Engineering Report — PWA / UI Track

**Date:** 2026-07-19  
**Status:** Complete  

## Scope

Responsive **installable PWA** (desktop/tablet/mobile browsers; **no native stores**) consuming Phase 2–3 APIs with real Google OAuth and RBAC.

## Architecture outcomes

| Layer | Outcome |
|-------|---------|
| Auth | Google ID token → API verify → domain allowlist → Firestore `users/{uid}` roles |
| Identity | `GET /api/v1/me` |
| Chat | `POST /api/v1/query/answer` with refusal + citations |
| Admin | Upload + list/get + publish/retire (content_admin\|admin) |
| Deploy safety | Frontend polls `/health`; hard reload on `version`/`deployed_at` change |
| PWA | Manifest + SW; offline shell only |

## Key defaults (ops)

| Setting | Default (Phase 5.4) |
|---------|---------------------|
| `GENERATION_MODEL_ID` | `gemini-2.5-flash` |
| `VERTEX_LOCATION` | `asia-south1` (embeddings + generation region) |
| Allowed domains | `chandraailabs.com`, `gmail.com` |

## Test posture

- Backend unit/API tests (mocked Vertex/GCS/Firestore; auth helpers).  
- Frontend typecheck + pure helper checks.  
- Live E2E: Coordinator OAuth secrets + published docs (documented, not fully CI-automated).

## Artifacts

- ADRs: 0009, 0010  
- Runbooks: oauth-and-frontend-auth, pwa-install, grounded-answer-api  
- Retro: [phase-5.md](../retrospectives/phase-5.md)  

## Recommendation

Close Phase 5 as **MVP complete**. Open Phase 4 design for retrieval quality without blocking on further UI polish unless product prioritizes voice/feedback next.
