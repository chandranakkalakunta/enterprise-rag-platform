# Runbook: OAuth + frontend auth (Phase 5.1)

**Status:** Implementation live (ADR-0009 / ADR-0010)  
**Secrets:** `rag-oauth-client-id`, `rag-oauth-client-secret` (CMEK shells from Phase 1.3)  
**Related:** [oauth-domain-allowlist.md](./oauth-domain-allowlist.md) · [secret-manager-cmek.md](./secret-manager-cmek.md)

---

## What was implemented

| Layer | Behavior |
|-------|----------|
| AuthN | Google **ID token** verified on API (`audience` = `GOOGLE_OAUTH_CLIENT_ID`) |
| Domain | `ALLOWED_EMAIL_DOMAINS` default `chandraailabs.com,gmail.com` — checked every request |
| Profiles | Firestore `users/{uid}` upsert on `/me` and protected routes |
| Roles | `viewer` \| `content_admin` \| `admin`; bootstrap via `ADMIN_EMAILS` / `CONTENT_ADMIN_EMAILS` |
| Identity API | `GET /api/v1/me` → `{ uid, email, name, picture, role }` |
| Protected | Upload / publish / retire require **content_admin** or **admin**; search / answer require **any** authenticated allowlisted user |
| Public | `/health`, `/ready`, `/`, OpenAPI docs |
| Frontend session | GIS ID token in memory + `sessionStorage`; `Authorization: Bearer` |
| Version reload | Frontend polls `/health`; full reload if `version` or `deployed_at` changes |

`AUTH_DEV_BYPASS=true` remains **local/tests only** (injects fake admin). Shared environments must set `AUTH_DEV_BYPASS=false`.

---

## Coordinator: create OAuth client

1. Google Cloud Console → **APIs & Services** → **Credentials**  
   Project: `enterprise-rag-platform-502711` (or active env project).
2. **Configure OAuth consent screen** (if not done):
   - User type: **External** (or Internal if Workspace-only later)
   - App name: Enterprise RAG Platform  
   - Support email: your org admin  
   - Scopes: `openid`, `email`, `profile`  
   - Test users: add bootstrap admin Gmail / workspace accounts while app is in Testing
3. **Create credentials** → **OAuth client ID** → Application type **Web application**
4. Authorized JavaScript origins (examples):
   - `http://localhost:3000`
   - Cloud Run web URL later (`https://rag-web-….run.app`)
5. Authorized redirect URIs: not required for GIS **popup / One Tap ID token** flow; add if switching to auth-code later.
6. Copy **Client ID** and **Client secret**.

---

## Coordinator: Secret Manager versions

```bash
PROJECT_ID=enterprise-rag-platform-502711
REGION=asia-south1

# Client ID (also used by frontend NEXT_PUBLIC_GOOGLE_CLIENT_ID)
printf '%s' 'YOUR_CLIENT_ID.apps.googleusercontent.com' | \
  gcloud secrets versions add rag-oauth-client-id \
    --project="${PROJECT_ID}" --data-file=-

# Client secret (server-side only if auth-code / future BFF; ID-token MVP may not need it on API)
printf '%s' 'YOUR_CLIENT_SECRET' | \
  gcloud secrets versions add rag-oauth-client-secret \
    --project="${PROJECT_ID}" --data-file=-
```

Wire client id into Cloud Run `rag-api` env (or secret ref) as **`GOOGLE_OAUTH_CLIENT_ID`**.

---

## Coordinator: bootstrap admins

On `rag-api` (Cloud Run env / Secret Manager):

| Variable | Example | Effect |
|----------|---------|--------|
| `ADMIN_EMAILS` | `you@chandraailabs.com,you@gmail.com` | Those emails → role `admin` on login |
| `CONTENT_ADMIN_EMAILS` | `ops@gmail.com` | → `content_admin` if not admin |
| `ALLOWED_EMAIL_DOMAINS` | `chandraailabs.com,gmail.com` | Default if unset |
| `AUTH_DEV_BYPASS` | **`false`** | Required outside local/CI unit tests |
| `GOOGLE_OAUTH_CLIENT_ID` | Web client id | Token audience |

Default role for any other allowlisted user: **`viewer`**.

---

## Local development

### API

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export AUTH_DEV_BYPASS=false
export GOOGLE_OAUTH_CLIENT_ID='….apps.googleusercontent.com'
export ADMIN_EMAILS='you@gmail.com'
export ALLOWED_EMAIL_DOMAINS='chandraailabs.com,gmail.com'
export GCP_PROJECT_ID=enterprise-rag-platform-502711
# ADC for Firestore: gcloud auth application-default login

uvicorn app.main:app --reload --port 8000
```

Quick test without Google (unit tests only):

```bash
export AUTH_DEV_BYPASS=true
pytest -q
# GET /api/v1/me returns dev@chandraailabs.com role=admin
```

### Frontend

```bash
cd frontend
cp .env.example .env.local
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
# NEXT_PUBLIC_GOOGLE_CLIENT_ID=….apps.googleusercontent.com

npm install
npm run dev
```

Open `http://localhost:3000/login` → Sign in with Google → Chat home; Admin link if elevated role.

---

## `/me` response schema

```json
{
  "uid": "google-subject-sub",
  "email": "user@gmail.com",
  "name": "Display Name",
  "picture": "https://…",
  "role": "viewer"
}
```

`role` is always from backend/Firestore after bootstrap resolution.

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| 401 on `/me` | Missing Bearer; wrong/expired ID token; `GOOGLE_OAUTH_CLIENT_ID` mismatch with GIS client |
| 403 domain | Email domain not in allowlist |
| 403 on upload | User role is `viewer` — add to `CONTENT_ADMIN_EMAILS` or `ADMIN_EMAILS` and re-login |
| GIS button missing | `NEXT_PUBLIC_GOOGLE_CLIENT_ID`; authorized JS origin includes current host |
| CORS errors | API `CORS_ALLOW_ORIGINS` includes frontend origin (default localhost:3000) |
| Version reload loop | Ensure `/health` returns stable `version`/`deployed_at` for a given deploy |

---

## Residual risks

- ID token in `sessionStorage` is readable under XSS (MVP trade-off; consider httpOnly BFF later).
- Gmail allowlist is broad (any gmail can become viewer if they can reach the URL).
- Live OAuth E2E requires Coordinator secret fill + consent test users — not fully automated in CI.
