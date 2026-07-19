"use client";

import {
  useCallback,
  useId,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { SendHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ComposerProps {
  onSend: (text: string) => void | Promise<void>;
  disabled?: boolean;
  placeholder?: string;
  /** Previous user prompts for ArrowUp cycling (newest last). */
  promptHistory?: string[];
}

/**
 * Keyboard:
 * - Enter sends; Shift+Enter inserts a newline
 * - ArrowUp cycles previous user prompts (session-local history)
 * - ArrowDown moves toward newer / draft
 */
export function Composer({
  onSend,
  disabled = false,
  placeholder = "Ask about published documents…",
  promptHistory = [],
}: ComposerProps) {
  const [value, setValue] = useState("");
  const inputId = useId();
  const helpId = useId();
  const trimmed = value.trim();
  const canSend = !disabled && trimmed.length > 0;

  /** Index into promptHistory from the end; -1 = live draft. */
  const historyIndex = useRef(-1);
  const draftRef = useRef("");

  const submit = useCallback(async () => {
    if (!canSend) return;
    const text = trimmed;
    setValue("");
    historyIndex.current = -1;
    draftRef.current = "";
    await onSend(text);
  }, [canSend, onSend, trimmed]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void submit();
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
      return;
    }

    if (e.key === "ArrowUp" && promptHistory.length > 0) {
      const el = e.currentTarget;
      const atStart =
        el.selectionStart === 0 && el.selectionEnd === 0;
      // Cycle when empty or caret at start (common REPL pattern)
      if (value === "" || atStart) {
        e.preventDefault();
        if (historyIndex.current === -1) {
          draftRef.current = value;
        }
        const next = Math.min(
          historyIndex.current + 1,
          promptHistory.length - 1,
        );
        historyIndex.current = next;
        const entry = promptHistory[promptHistory.length - 1 - next];
        if (entry != null) setValue(entry);
      }
      return;
    }

    if (e.key === "ArrowDown" && historyIndex.current >= 0) {
      const el = e.currentTarget;
      const atEnd =
        el.selectionStart === value.length &&
        el.selectionEnd === value.length;
      if (atEnd || value === promptHistory[promptHistory.length - 1 - historyIndex.current]) {
        e.preventDefault();
        const next = historyIndex.current - 1;
        if (next < 0) {
          historyIndex.current = -1;
          setValue(draftRef.current);
        } else {
          historyIndex.current = next;
          const entry = promptHistory[promptHistory.length - 1 - next];
          if (entry != null) setValue(entry);
        }
      }
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="border-t border-border bg-card/80 p-3 backdrop-blur sm:p-4"
    >
      <label htmlFor={inputId} className="sr-only">
        Message
      </label>
      <div className="flex items-end gap-2">
        <textarea
          id={inputId}
          name="message"
          rows={1}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            if (historyIndex.current === -1) {
              draftRef.current = e.target.value;
            }
          }}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          aria-describedby={helpId}
          className={cn(
            "min-h-[44px] max-h-36 w-full resize-y rounded-xl border border-input bg-background px-3 py-2.5 text-sm leading-5 shadow-sm",
            "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            "disabled:cursor-not-allowed disabled:opacity-60",
          )}
        />
        <Button
          type="submit"
          size="default"
          disabled={!canSend}
          aria-label="Send message"
          className="h-11 shrink-0 rounded-xl px-3 sm:px-4"
        >
          <SendHorizontal className="h-4 w-4" aria-hidden />
          <span className="hidden sm:inline">Send</span>
        </Button>
      </div>
      <p id={helpId} className="mt-1.5 text-[11px] text-muted-foreground">
        Enter to send · Shift+Enter newline · ↑ previous prompts ·{" "}
        <code className="rounded bg-muted px-0.5">/clear</code> clears chat
      </p>
    </form>
  );
}
