"use client";

import { AlertTriangle, Bot, User } from "lucide-react";

import { CitationList } from "@/components/chat/citation-list";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isRefusal = !isUser && message.refused === true;

  return (
    <article
      className={cn(
        "flex gap-3",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
      aria-label={isUser ? "Your message" : "Assistant message"}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
          isRefusal && "bg-amber-100 text-amber-800",
        )}
        aria-hidden
      >
        {isUser ? (
          <User className="h-4 w-4" />
        ) : isRefusal ? (
          <AlertTriangle className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </div>

      <div
        className={cn(
          "max-w-[min(100%,36rem)] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
          isUser &&
            "rounded-tr-md bg-primary text-primary-foreground",
          !isUser &&
            !isRefusal &&
            "rounded-tl-md border border-border bg-card text-card-foreground",
          isRefusal &&
            "rounded-tl-md border border-amber-200 bg-amber-50 text-amber-950",
        )}
      >
        {isRefusal && (
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-800">
            Insufficient evidence
          </p>
        )}
        <div className="whitespace-pre-wrap break-words">{message.content}</div>
        {isRefusal && message.refusalReason && (
          <p className="mt-2 text-xs text-amber-800/80">
            Reason: {message.refusalReason}
          </p>
        )}
        {!isUser &&
          !isRefusal &&
          message.citations &&
          message.citations.length > 0 && (
            <CitationList citations={message.citations} />
          )}
      </div>
    </article>
  );
}
