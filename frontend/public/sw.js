/**
 * Enterprise RAG Platform — app shell service worker (Phase 5.4 / ADR-0010).
 *
 * - Precache shell assets only
 * - Offline: offline.html shell (no answers)
 * - Never cache /api/* on this origin
 * - Cross-origin (backend API) is not intercepted for caching
 * - Version auto-reload (VersionWatcher → /health) is API-origin; unaffected
 */

const CACHE_NAME = "erp-shell-v1";
const PRECACHE = [
  "/",
  "/offline.html",
  "/manifest.webmanifest",
  "/icon.svg",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

function isApiPath(pathname) {
  return pathname === "/api" || pathname.startsWith("/api/");
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") {
    return;
  }

  const url = new URL(req.url);

  // Cross-origin (e.g. Cloud Run API) — browser default; do not cache answers
  if (url.origin !== self.location.origin) {
    return;
  }

  // Same-origin API proxies (if any) — network only
  if (isApiPath(url.pathname)) {
    event.respondWith(fetch(req));
    return;
  }

  // Navigations: network-first, fall back to cached page or offline shell
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE_NAME).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() =>
          caches
            .match(req)
            .then((cached) => cached || caches.match("/offline.html")),
        ),
    );
    return;
  }

  // Static same-origin: cache-first with network update
  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE_NAME).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});
