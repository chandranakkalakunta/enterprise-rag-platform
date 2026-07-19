# Frontend — Enterprise RAG Platform

Next.js **15** App Router PWA shell (Phase 5.1 / [ADR-0010](../docs/adr/0010-pwa-shell-version-reload.md)).

## Stack

- Next.js 15 + React 19 + TypeScript
- Tailwind CSS + lightweight shadcn-style `Button`
- Google Identity Services (ID token → `Authorization: Bearer`)
- Roles from backend `GET /api/v1/me` ([ADR-0009](../docs/adr/0009-authn-authz-user-profiles.md))
- **Version watcher:** polls `/health`; full reload if `version` or `deployed_at` changes

## Session model (MVP)

1. User signs in with Google (GIS) → browser receives **Google ID token**.
2. Frontend stores token in **memory + `sessionStorage`** (`erp_google_id_token`).
3. Calls API with `Authorization: Bearer <id_token>`.
4. Backend verifies token (audience = OAuth client id), domain allowlist, upserts Firestore `users/{uid}`, returns role.

**Not** used yet: BFF + httpOnly cookie. Documented residual risk: XSS can read sessionStorage tokens; harden later if needed.

## Local run

```bash
cp .env.example .env.local
# set NEXT_PUBLIC_API_BASE_URL and NEXT_PUBLIC_GOOGLE_CLIENT_ID

npm install
npm run dev
# http://localhost:3000
```

API must have matching `GOOGLE_OAUTH_CLIENT_ID` and `AUTH_DEV_BYPASS=false` for real OAuth.

## Manual checklist

- [ ] Login with allowlisted Google account → redirected to Chat
- [ ] Domain-denied account → API 403 message on login
- [ ] Admin / content_admin → Admin nav link visible
- [ ] Viewer → no Admin link; `/admin` redirects home
- [ ] Change API `APP_VERSION` or `DEPLOYED_AT` → UI reloads within poll / focus
- [ ] `/health` works without auth

## PWA

- `public/manifest.webmanifest` + icon (installable baseline)
- Full service worker offline shell can land in Phase 5.2 if split cleaner
