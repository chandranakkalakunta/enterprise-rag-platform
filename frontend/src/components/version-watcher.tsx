"use client";

/**
 * ADR-0010: poll backend /health; force full reload if version or deployed_at changes.
 * First successful read stores baseline without reload.
 */

import { useEffect, useRef } from "react";

import { fetchHealth } from "@/lib/api";
import { getHealthPollMs } from "@/lib/config";

const KEY_VERSION = "erp_backend_version";
const KEY_DEPLOYED = "erp_backend_deployed_at";

export function VersionWatcher() {
  const checking = useRef(false);

  useEffect(() => {
    async function check() {
      if (checking.current) return;
      checking.current = true;
      try {
        const health = await fetchHealth();
        const version = health.version ?? "";
        const deployedAt = health.deployed_at ?? "";
        const lastV = sessionStorage.getItem(KEY_VERSION);
        const lastD = sessionStorage.getItem(KEY_DEPLOYED);

        if (lastV === null && lastD === null) {
          sessionStorage.setItem(KEY_VERSION, version);
          sessionStorage.setItem(KEY_DEPLOYED, deployedAt);
          return;
        }

        if (version !== lastV || deployedAt !== lastD) {
          sessionStorage.setItem(KEY_VERSION, version);
          sessionStorage.setItem(KEY_DEPLOYED, deployedAt);
          window.location.reload();
        }
      } catch {
        // Health may be down during deploys; do not thrash reloads
      } finally {
        checking.current = false;
      }
    }

    void check();
    const intervalMs = getHealthPollMs();
    const timer = window.setInterval(() => void check(), intervalMs);

    const onFocus = () => void check();
    const onVisibility = () => {
      if (document.visibilityState === "visible") void check();
    };

    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return null;
}
