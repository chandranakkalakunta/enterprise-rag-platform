/**
 * Pure helpers for chat UI (unit-testable without React).
 */

import type { AnswerCitation, AnswerResponse, ChatMessage } from "@/lib/types";

export function buildAssistantMessage(
  result: AnswerResponse,
  id: string,
  createdAt: number = Date.now(),
): ChatMessage {
  return {
    id,
    role: "assistant",
    content: result.answer,
    refused: result.refused,
    refusalReason: result.refusal_reason,
    citations: result.refused ? [] : (result.citations ?? []),
    createdAt,
  };
}

export function formatCitationScore(score: number): string {
  return score.toFixed(3);
}

export function citationDisplayTitle(
  c: AnswerCitation,
  index: number,
): string {
  const title = c.title?.trim() || c.filename?.trim();
  if (title) return title;
  if (c.document_id) return `Document ${c.document_id.slice(0, 8)}…`;
  return `Source ${index + 1}`;
}

/** Exact local command — clears chat without calling the answer API. */
export function isClearCommand(text: string): boolean {
  return text.trim() === "/clear";
}

/**
 * Cycle into previous prompts (newest at end of history).
 * historyIndex -1 means draft; 0 is most recent prompt.
 */
export function historyEntryAt(
  history: string[],
  historyIndexFromNewest: number,
): string | undefined {
  if (historyIndexFromNewest < 0 || historyIndexFromNewest >= history.length) {
    return undefined;
  }
  return history[history.length - 1 - historyIndexFromNewest];
}
