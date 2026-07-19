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
