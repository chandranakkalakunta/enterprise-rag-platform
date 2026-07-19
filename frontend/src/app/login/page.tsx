"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { GoogleSignInButton } from "@/components/google-sign-in-button";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const { user, loading, error } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace("/");
    }
  }, [user, loading, router]);

  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-6 rounded-lg border border-border bg-card p-8 shadow-sm">
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="text-sm text-muted-foreground">
          Google accounts on <strong>chandraailabs.com</strong> or{" "}
          <strong>gmail.com</strong> only. Other domains are rejected by the API
          after OAuth.
        </p>
      </div>

      <GoogleSignInButton />

      {error && (
        <p className="text-center text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <p className="text-xs text-muted-foreground">
        Roles come from <code className="rounded bg-muted px-1">GET /api/v1/me</code>{" "}
        (backend source of truth). Session: Google ID token in memory +
        sessionStorage, sent as Bearer on API calls.
      </p>
    </div>
  );
}
