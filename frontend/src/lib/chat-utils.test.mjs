/**
 * Minimal pure-function checks (no test runner required).
 * Run: node src/lib/chat-utils.test.mjs  (from frontend/ after build not needed —
 * logic is inlined below to avoid TS loader).
 */

function buildAssistantMessage(result, id, createdAt = Date.now()) {
  return {
    id,
    role: "assistant",
    content: result.answer,
    refused: result.refused,
    refusalReason: result.refusal_reason,
    citations: result.refused ? [] : result.citations ?? [],
    createdAt,
  };
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

const ok = buildAssistantMessage(
  {
    query: "q",
    answer: "A",
    refused: false,
    refusal_reason: null,
    citations: [{ snippet: "s", score: 0.9, document_id: "d", version_id: "v", chunk_index: 0, title: "T", filename: "f.md" }],
    retrieval: { top_k: 5, hit_count: 1 },
  },
  "id-1",
  1,
);
assert(ok.content === "A", "answer text");
assert(ok.citations.length === 1, "citations kept");
assert(ok.refused === false, "not refused");

const refused = buildAssistantMessage(
  {
    query: "q",
    answer: "Cannot answer",
    refused: true,
    refusal_reason: "no_hits",
    citations: [{ snippet: "leak", score: 0.1, document_id: null, version_id: null, chunk_index: null, title: null, filename: null }],
    retrieval: { top_k: 5, hit_count: 0 },
  },
  "id-2",
  2,
);
assert(refused.refused === true, "refused flag");
assert(refused.citations.length === 0, "no fake citations on refusal");
assert(refused.refusalReason === "no_hits", "refusal reason");

function meaningfulCitationField(value) {
  const t = value?.trim?.() ?? (typeof value === "string" ? value.trim() : value);
  if (!t) return null;
  if (String(t).toLowerCase() === "untitled") return null;
  return t;
}
function citationDisplayTitle(c, index) {
  const title =
    meaningfulCitationField(c.title) || meaningfulCitationField(c.filename);
  if (title) return title;
  if (c.document_id) return `Document ${c.document_id.slice(0, 8)}…`;
  return `Source ${index + 1}`;
}
function isClearCommand(text) {
  return text.trim() === "/clear";
}
function historyEntryAt(history, historyIndexFromNewest) {
  if (historyIndexFromNewest < 0 || historyIndexFromNewest >= history.length) {
    return undefined;
  }
  return history[history.length - 1 - historyIndexFromNewest];
}

assert(isClearCommand("/clear") === true, "/clear exact");
assert(isClearCommand(" /clear ") === true, "/clear trim");
assert(isClearCommand("/clear now") === false, "/clear not prefix");
assert(historyEntryAt(["a", "b", "c"], 0) === "c", "newest");
assert(historyEntryAt(["a", "b", "c"], 1) === "b", "prev");
assert(historyEntryAt(["a", "b", "c"], 2) === "a", "oldest");
assert(historyEntryAt(["a"], 1) === undefined, "oob");

assert(
  citationDisplayTitle({ title: "Untitled", filename: "policy.md" }, 0) ===
    "policy.md",
  "Untitled falls back to filename",
);
assert(
  citationDisplayTitle({ title: null, filename: "a.pdf" }, 0) === "a.pdf",
  "filename only",
);
assert(
  citationDisplayTitle({ title: "Leave Policy", filename: "a.md" }, 0) ===
    "Leave Policy",
  "real title wins",
);
assert(
  citationDisplayTitle({ title: null, filename: null, document_id: null }, 2) ===
    "Source 3",
  "source fallback",
);

console.log("chat-utils.test.mjs: ok");
