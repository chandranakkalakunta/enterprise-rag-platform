"use client";

import { useCallback, useState } from "react";
import Link from "next/link";

import { Composer } from "@/components/chat/composer";
import { MessageList } from "@/components/chat/message-list";
import { ApiError, postAnswer } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { buildAssistantMessage } from "@/lib/chat-utils";
import type { ChatMessage } from "@/lib/types";

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function ChatPanel() {
  const { idToken, logout } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [promptHistory, setPromptHistory] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authExpired, setAuthExpired] = useState(false);

  const handleSend = useCallback(
    async (text: string) => {
      setError(null);
      setAuthExpired(false);

      // Exact local command — no API call (Phase 5.3)
      if (text.trim() === "/clear") {
        setMessages([
          {
            id: newId(),
            role: "assistant",
            content: "Chat cleared (local only — not stored on the server).",
            createdAt: Date.now(),
          },
        ]);
        return;
      }

      setPromptHistory((prev) => {
        // Avoid consecutive duplicates
        if (prev[prev.length - 1] === text) return prev;
        return [...prev, text];
      });

      const userMsg: ChatMessage = {
        id: newId(),
        role: "user",
        content: text,
        createdAt: Date.now(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const result = await postAnswer({ query: text, top_k: 5 }, idToken);
        const assistant = buildAssistantMessage(result, newId());
        setMessages((prev) => [...prev, assistant]);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          setAuthExpired(true);
          setError(err.message);
        } else if (err instanceof ApiError) {
          setError(err.message);
        } else if (err instanceof Error) {
          setError(err.message || "Network error — could not reach the API");
        } else {
          setError("Unexpected error while getting an answer");
        }
      } finally {
        setLoading(false);
      }
    },
    [idToken],
  );

  return (
    <div className="flex min-h-[min(70vh,640px)] flex-1 flex-col overflow-hidden rounded-xl border border-border bg-background shadow-sm">
      <MessageList messages={messages} loading={loading} />

      {error && (
        <div
          className="mx-3 mb-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900 sm:mx-4"
          role="alert"
        >
          <p>{error}</p>
          {authExpired && (
            <p className="mt-2 flex flex-wrap gap-3">
              <button
                type="button"
                className="font-medium underline underline-offset-2"
                onClick={() => {
                  logout();
                }}
              >
                Sign out
              </button>
              <Link
                href="/login"
                className="font-medium underline underline-offset-2"
              >
                Sign in again
              </Link>
            </p>
          )}
        </div>
      )}

      <Composer
        onSend={handleSend}
        disabled={loading}
        promptHistory={promptHistory}
      />
    </div>
  );
}
