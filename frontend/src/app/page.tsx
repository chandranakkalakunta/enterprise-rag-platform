"use client";

import Link from "next/link";
import { MessageSquare } from "lucide-react";

import { ChatPanel } from "@/components/chat/chat-panel";
import { useAuth } from "@/lib/auth-context";

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
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold tracking-tight sm:text-2xl">
            <MessageSquare className="h-5 w-5 text-primary sm:h-6 sm:w-6" aria-hidden />
            Chat
          </h1>
          <p className="mt-0.5 text-xs text-muted-foreground sm:text-sm">
            Grounded answers with citations · {user.email}
          </p>
        </div>
      </div>

      <ChatPanel />
    </div>
  );
}
