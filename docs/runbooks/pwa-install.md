# Runbook: PWA install (Phase 5.4 / ADR-0010)

## Behaviour

| Item | Detail |
|------|--------|
| Manifest | `/manifest.webmanifest` — name, short_name, start_url `/`, display `standalone`, icons 192/512 PNG + SVG |
| Service worker | `/sw.js` — precaches app shell + offline page |
| Offline | **Shell only** (`/offline.html` or cached navigate). **No** offline answers or API cache |
| API | Cross-origin backend is not SW-cached; same-origin `/api/*` is network-only |
| Version reload | Client polls backend `/health` (API origin) — unaffected by SW shell cache |

## Install (manual)

### Desktop Chrome / Edge

1. Serve frontend over **HTTPS** (or `localhost`).  
2. Open the app; wait for SW registration (Application → Service Workers).  
3. Install via address-bar install icon or menu **Install app**.  
4. Criteria typically: valid manifest + icons ≥192 + registered SW + HTTPS.

### Mobile Safari (iOS)

- **Add to Home Screen** from Share menu (uses `apple-touch-icon` + manifest).  
- Installability differs from Chromium; no classic “install prompt” on all iOS versions.

### After deploy

- VersionWatcher still force-reloads when API `version` / `deployed_at` changes.  
- SW updates via `skipWaiting` + `clients.claim` on next navigation/load.

## Local

```bash
cd frontend
npm run dev
# open http://localhost:3000 — SW registers after load
```

Production Cloud Run web (`rag-web`) should serve `public/` assets including `sw.js` and manifest.

## Related

- [ADR-0010](../adr/0010-pwa-shell-version-reload.md)  
- [frontend/README.md](../../frontend/README.md)  
