"use client";

/**
 * Registers the shell service worker (Phase 5.4).
 * Does not interfere with VersionWatcher (API /health is cross-origin).
 */

import { useEffect } from "react";

export function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!("serviceWorker" in navigator)) return;
    // Avoid SW noise during Next.js HMR in local dev if desired — still OK to register
    const onLoad = () => {
      navigator.serviceWorker
        .register("/sw.js", { scope: "/" })
        .catch((err) => {
          console.warn("Service worker registration failed", err);
        });
    };
    if (document.readyState === "complete") {
      onLoad();
    } else {
      window.addEventListener("load", onLoad);
      return () => window.removeEventListener("load", onLoad);
    }
  }, []);

  return null;
}
