"use client";

import { useEffect, useRef, useState } from "react";

import { getGoogleClientId } from "@/lib/config";
import { useAuth } from "@/lib/auth-context";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
            auto_select?: boolean;
            ux_mode?: string;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: Record<string, unknown>,
          ) => void;
          prompt: () => void;
        };
      };
    };
  }
}

const GIS_SRC = "https://accounts.google.com/gsi/client";

function loadGisScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.google?.accounts?.id) return Promise.resolve();
  const existing = document.querySelector<HTMLScriptElement>(
    `script[src="${GIS_SRC}"]`,
  );
  if (existing) {
    return new Promise((resolve, reject) => {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () =>
        reject(new Error("Failed to load Google Identity Services")),
      );
    });
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = GIS_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () =>
      reject(new Error("Failed to load Google Identity Services"));
    document.head.appendChild(script);
  });
}

export function GoogleSignInButton() {
  const buttonRef = useRef<HTMLDivElement>(null);
  const { loginWithIdToken } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const clientId = getGoogleClientId();

  useEffect(() => {
    if (!clientId || !buttonRef.current) return;
    let cancelled = false;

    (async () => {
      try {
        await loadGisScript();
        if (cancelled || !buttonRef.current || !window.google) return;

        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async (response) => {
            setBusy(true);
            setError(null);
            try {
              await loginWithIdToken(response.credential);
            } catch (err) {
              setError(
                err instanceof Error ? err.message : "Sign-in failed",
              );
            } finally {
              setBusy(false);
            }
          },
          auto_select: false,
          ux_mode: "popup",
        });

        buttonRef.current.innerHTML = "";
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: "outline",
          size: "large",
          text: "signin_with",
          shape: "rectangular",
          width: 280,
        });
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Could not load Google Sign-In",
          );
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [clientId, loginWithIdToken]);

  if (!clientId) {
    return (
      <p className="text-sm text-red-600">
        Set <code className="rounded bg-muted px-1">NEXT_PUBLIC_GOOGLE_CLIENT_ID</code>{" "}
        to enable Google Sign-In.
      </p>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <div ref={buttonRef} aria-label="Google Sign-In" />
      {busy && (
        <p className="text-sm text-muted-foreground">Verifying with API…</p>
      )}
      {error && (
        <p className="max-w-sm text-center text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
