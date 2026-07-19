"use client";

import { useEffect, useRef } from "react";
import { Loader2, MessageSquare } from "lucide-react";

import { MessageBubble } from "@/components/chat/message-bubble";
import type { ChatMessage } from "@/lib/types";

interface MessageListProps {
  messages: ChatMessage[];
  loading?: boolean;
}

export function MessageList({ messages, loading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  if (messages.length === 0 && !loading) {
    return (
      <div
        className="flex flex-1 flex-col items-center justify-center gap-3 px-4 py-12 text-center"
        role="status"
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <MessageSquare className="h-6 w-6 text-muted-foreground" aria-hidden />
        </div>
        <div className="max-w-sm space-y-1">
          <p className="font-medium">Ask a question</p>
          <p className="text-sm text-muted-foreground">
            Answers are grounded in published documents only. If evidence is
            missing, you will see a clear refusal — not a guess.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex flex-1 flex-col gap-4 overflow-y-auto px-1 py-2 sm:px-2"
      role="log"
      aria-live="polite"
      aria-relevant="additions"
    >
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
      {loading && (
        <div
          className="flex items-center gap-2 text-sm text-muted-foreground"
          role="status"
          aria-label="Waiting for answer"
        >
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Retrieving and generating answer…
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
