/**
 * Pure helpers for chat UI (unit-testable without React).
 */

import type { AnswerCitation, AnswerResponse, ChatMessage } from "@/lib/types";

/**
 * Safety-net dedupe by document_id (API also dedupes; keep max score).
 * maxPerDoc default 1 matches CITATION_MAX_PER_DOC.
 */
export function dedupeCitationsByDocument(
  citations: AnswerCitation[],
  maxPerDoc: number = 1,
): AnswerCitation[] {
  if (maxPerDoc < 1 || !citations.length) return [];
  const groups = new Map<string, AnswerCitation[]>();
  const order: string[] = [];
  for (const c of citations) {
    const key = (c.document_id || "").trim() || `__nodoc__:${order.length}`;
    if (!groups.has(key)) {
      groups.set(key, []);
      order.push(key);
    }
    groups.get(key)!.push(c);
  }
  const out: AnswerCitation[] = [];
  for (const key of order) {
    const group = (groups.get(key) || []).slice().sort((a, b) => b.score - a.score);
    out.push(...group.slice(0, maxPerDoc));
  }
  return out;
}

export function buildAssistantMessage(
  result: AnswerResponse,
  id: string,
  createdAt: number = Date.now(),
): ChatMessage {
  const raw = result.refused ? [] : (result.citations ?? []);
  return {
    id,
    role: "assistant",
    content: result.answer,
    refused: result.refused,
    refusalReason: result.refusal_reason,
    citations: dedupeCitationsByDocument(raw, 1),
    createdAt,
  };
}

export function formatCitationScore(score: number): string {
  return score.toFixed(3);
}

/**
 * Meaningful label: treat empty and generic "Untitled" as missing so filename wins.
 * Order: title || filename || document id snippet || "Source N"
 */
export function meaningfulCitationField(
  value: string | null | undefined,
): string | null {
  const t = value?.trim();
  if (!t) return null;
  if (t.toLowerCase() === "untitled") return null;
  return t;
}

export function citationDisplayTitle(
  c: AnswerCitation,
  index: number,
): string {
  const title =
    meaningfulCitationField(c.title) ||
    meaningfulCitationField(c.filename);
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
