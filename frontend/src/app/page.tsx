"use client";

import Link from "next/link";
import { MessageSquare } from "lucide-react";

import { useAuth } from "@/lib/auth-context";
import { getApiBaseUrl } from "@/lib/config";

export default function ChatHomePage() {
  const { user, loading } = useAuth();

  if (loading) {
    return <p className="text-muted-foreground">Loading session…</p>;
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-lg space-y-4 rounded-lg border border-border bg-card p-8 text-center shadow-sm">
        <h1 className="text-2xl font-semibold tracking-tight">
          Enterprise RAG Chat
        </h1>
        <p className="text-muted-foreground">
          Sign in with Google to ask questions against published knowledge.
          Anonymous access is not allowed.
        </p>
        <Link
          href="/login"
          className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
        >
          Sign in with Google
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
          <MessageSquare className="h-6 w-6 text-primary" aria-hidden />
          Chat
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Signed in as {user.email} ({user.role}). Full message UI lands in Phase
          5.2+; API is ready at{" "}
          <code className="rounded bg-muted px-1 text-xs">
            POST {getApiBaseUrl()}/api/v1/query/answer
          </code>
          .
        </p>
      </div>

      <div className="rounded-lg border border-dashed border-border bg-muted/40 p-8 text-center">
        <p className="text-sm text-muted-foreground">
          Chat composer and citation rendering arrive next. Backend{" "}
          <code className="text-xs">/api/v1/query/search</code> and{" "}
          <code className="text-xs">/answer</code> require a Google ID token
          (viewer+).
        </p>
      </div>
    </div>
  );
}
