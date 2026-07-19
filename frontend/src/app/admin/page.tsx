"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Shield } from "lucide-react";

import { DocumentList } from "@/components/admin/document-list";
import { UploadPanel } from "@/components/admin/upload-panel";
import { useAuth } from "@/lib/auth-context";
import { canAccessAdmin } from "@/lib/types";

export default function AdminPage() {
  const { user, loading, idToken } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (!canAccessAdmin(user.role)) {
      router.replace("/");
    }
  }, [user, loading, router]);

  const onError = useCallback((message: string) => {
    setSuccess(null);
    setError(message);
  }, []);

  const onSuccess = useCallback((message: string) => {
    setError(null);
    setSuccess(message);
  }, []);

  if (loading || !user || !canAccessAdmin(user.role)) {
    return <p className="text-muted-foreground">Checking access…</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold tracking-tight sm:text-2xl">
            <Shield className="h-5 w-5 text-primary sm:h-6 sm:w-6" aria-hidden />
            Admin
          </h1>
          <p className="mt-0.5 text-xs text-muted-foreground sm:text-sm">
            Role <strong>{user.role}</strong> · mutations enforced by API (403 if
            unauthorized)
          </p>
        </div>
        <Link
          href="/"
          className="text-sm text-primary underline-offset-4 hover:underline"
        >
          ← Chat
        </Link>
      </div>

      {error && (
        <div
          className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900"
          role="alert"
        >
          {error}
          <button
            type="button"
            className="ml-3 text-xs font-medium underline"
            onClick={() => setError(null)}
          >
            Dismiss
          </button>
        </div>
      )}
      {success && (
        <div
          className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-950"
          role="status"
        >
          {success}
          <button
            type="button"
            className="ml-3 text-xs font-medium underline"
            onClick={() => setSuccess(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      <UploadPanel
        idToken={idToken}
        onError={onError}
        onUploaded={(result) => {
          onSuccess(
            `Uploaded ${result.filename} → ${result.status} (${result.document_id})`,
          );
          setRefreshKey((k) => k + 1);
        }}
      />

      <DocumentList
        idToken={idToken}
        refreshKey={refreshKey}
        onError={onError}
        onSuccess={onSuccess}
      />
    </div>
  );
}
