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

## Chat (Phase 5.2)

Home route is the chat UI:

- Composer + message list (user / assistant)
- `POST /api/v1/query/answer` with `Authorization: Bearer <Google ID token>`
- Body: `{ "query": "<text>", "top_k": 5 }`
- Renders answer text; **refusal** banner when `refused=true` (no citations shown)
- Citations: title/filename, snippet, score
- **Keyboard:** Enter sends; Shift+Enter newline

## Manual checklist

### Auth shell (5.1)
- [ ] Login with allowlisted Google account → redirected to Chat
- [ ] Domain-denied account → API 403 message on login
- [ ] Admin / content_admin → Admin nav link visible
- [ ] Viewer → no Admin link; `/admin` redirects home
- [ ] Change API `APP_VERSION` or `DEPLOYED_AT` → UI reloads within poll / focus
- [ ] `/health` works without auth

### Chat (5.2–5.3)
- [ ] Signed-in user can send a question; assistant bubble appears
- [ ] Loading indicator while waiting for answer; send disabled while in-flight
- [ ] Empty input cannot send
- [ ] Refusal path: clear “Insufficient evidence” UI when no published docs / refuse
- [ ] Citations listed under successful answers (snippet, title/filename, score)
- [ ] Enter sends; Shift+Enter inserts newline
- [ ] **↑** cycles previous user prompts; **↓** returns toward draft
- [ ] **`/clear`** (exact) clears local messages (system note; no API call)
- [ ] Network/API error shows alert; 401 offers re-login
- [ ] Usable on narrow mobile width (~320–390px)

### Admin (5.3)
- [ ] Viewer: no Admin nav; `/admin` redirects home
- [ ] content_admin/admin: Admin page with upload form
- [ ] Upload PDF/MD ≤50MB → shows document_id, version_id, status, gcs_uri
- [ ] Document list loads; expand shows versions with status badges
- [ ] Publish enabled only for `ready`; Retire for `ready`/`published`
- [ ] Backend 403 if role insufficient (even if UI mishandled)

## PWA

- `public/manifest.webmanifest` + icon (installable baseline)
- Full service worker offline shell can land later (Phase 5.3+)
