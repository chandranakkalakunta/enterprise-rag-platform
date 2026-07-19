"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Shield } from "lucide-react";

import { useAuth } from "@/lib/auth-context";
import { canAccessAdmin } from "@/lib/types";

export default function AdminPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

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

  if (loading || !user || !canAccessAdmin(user.role)) {
    return <p className="text-muted-foreground">Checking access…</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
          <Shield className="h-6 w-6 text-primary" aria-hidden />
          Admin
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Visible because your backend role is <strong>{user.role}</strong>.
          Document upload / publish UI lands in Phase 5.2+. Mutations still require
          content_admin or admin on the API.
        </p>
      </div>

      <div className="rounded-lg border border-border bg-card p-6 text-sm">
        <ul className="list-disc space-y-2 pl-5 text-muted-foreground">
          <li>
            Upload:{" "}
            <code className="text-xs">POST /api/v1/documents/upload</code>
          </li>
          <li>
            Publish / retire:{" "}
            <code className="text-xs">
              POST /api/v1/documents/{"{id}"}/versions/{"{vid}"}/publish|retire
            </code>
          </li>
        </ul>
        <p className="mt-4">
          <Link href="/" className="text-primary underline-offset-4 hover:underline">
            ← Back to Chat
          </Link>
        </p>
      </div>
    </div>
  );
}
