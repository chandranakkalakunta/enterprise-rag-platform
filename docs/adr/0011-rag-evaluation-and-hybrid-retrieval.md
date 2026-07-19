# ADR-0011: RAG Evaluation and Hybrid Retrieval

## Status

Accepted — 2026-07-19

## Context

Phase 3 delivered **dense-only** retrieval (Vertex Vector Search) and grounded generation ([ADR-0007](./0007-embedding-and-vector-search.md), [ADR-0008](./0008-retrieval-and-grounded-generation.md)). Phase 5 shipped the PWA against that contract. Live usage shows quality gaps that are **measurable and addressable**:

| Observed issue | Likely driver |
|----------------|---------------|
| Incomplete **list** answers | Low `top_k` / chunk coverage; generation truncates multi-item evidence |
| **Same document** repeated in citations | Rank list dominated by multiple chunks from one doc |
| Misses on **exact headings / tables / keywords** | Dense-only weak on lexical match |
| No **held-out scoreboard** | Changes to retrieve/generate are unmeasured (risk of silent regressions) |

Forces:

1. **Eval first** — improve only with baseline + golden-set evidence (enterprise non-negotiable)  
2. Prefer **extending LangGraph `retrieve`** over a new product API surface  
3. **Pragmatic BM25** — in-process index for MVP scale; managed OpenSearch later if ops demand  
4. Keep **published/active-only** scope (ADR-0003 / 0007)  
5. Fusion must be **simple, standard, and tunable** → Reciprocal Rank Fusion (RRF)  
6. Out of scope for this ADR: full agentic multi-tool loops, voice, replacing Vector Search  

## Decision

### 1. Evaluation precedes retrieval algorithm changes

Phase **4.1** lands an evaluation harness and golden set **before** hybrid retrieve ships in production default path.

| Element | Choice |
|---------|--------|
| Golden set | Domain questions covering: factual lookup, **list/table**, multi-hop light, **refusal** (no evidence), and known dense-miss / lexical cases |
| Storage | Versioned under repo (e.g. `eval/golden/` JSON/JSONL) — questions, expected doc/chunk ids or keywords, refusal flags; **no production PII** |
| Baseline | Run dense-only (`POST /api/v1/query/search` + `/answer`) on golden set; record metrics once; gate later changes against this baseline |
| Cadence | Re-run on PR when retrieval/generation code changes (CI job optional in 4.1; required smoke for 4.2+) |

**Primary metrics (Phase 4.x):**

| Metric | Layer | Purpose |
|--------|-------|---------|
| **Recall@k** | Retrieval | Share of questions where expected evidence appears in top-k fused (or dense-only baseline) hits |
| **Groundedness / faithfulness** | Answer | Claims supported by retrieved snippets (LLM-as-judge and/or citation overlap; start simple) |
| **List completeness** | Answer | For list-type questions: fraction of expected items present in the answer |
| **Refusal correctness** | Answer | Refuse when no evidence; **do not** refuse when evidence exists |

Secondary (optional later): latency p50/p95, citation uniqueness, cost per query.

### 2. Hybrid retrieval: dense + BM25 + RRF

| Channel | Source | Scope |
|---------|--------|-------|
| **Dense** | Existing Vertex AI Vector Search | `active=true` published chunks only (unchanged lifecycle) |
| **BM25** | Lexical index over **published chunk text** | Same published-only scope; built from chunk payloads (GCS `chunks.jsonl` / index reload on publish-retire) |
| **Fusion** | **Reciprocal Rank Fusion (RRF)** | Combine ranked lists into a single ordered list before evidence_check |

RRF score form (standard): for each document/chunk id \(d\),

\[
\text{RRF}(d) = \sum_{r \in \text{rankers}} \frac{1}{k + \text{rank}_r(d)}
\]

with configurable \(k\) (typical default **60**). Final top_k after fusion feeds the existing evidence and generate nodes.

### 3. LangGraph: extend `retrieve`, do not fork the product surface

Keep existing public APIs (`/api/v1/query/search`, `/api/v1/query/answer`) and graph shape:

```text
retrieve  →  evidence_check  →  generate | refuse
```

**Inside `retrieve` (Phase 4.2+):**

```text
query
  ├─ dense_retrieve (Vector Search)  ──┐
  └─ bm25_retrieve (published chunks) ─┴─→ RRF fuse → fused_hits (top_k)
```

- Parallel preferred when both channels are healthy; sequential fallback if one channel fails (document fail-open policy: dense-only if BM25 unavailable at startup, with metric flag).  
- **No new user-facing product** for hybrid vs dense — config flags may force dense-only for rollback (`HYBRID_RETRIEVAL_ENABLED`).  
- Search API may expose fused results when hybrid is on (same response schema).

### 4. BM25 implementation strategy (phased)

| Phase | Approach |
|-------|----------|
| **4.2 MVP** | **In-process BM25** over published chunk text (e.g. `rank_bm25` or equivalent), loaded into API memory (or sidecar) from published versions; **reload / patch on publish and retire** |
| **Later** | Optional **managed OpenSearch** (or equivalent) if corpus size, multi-instance consistency, or ops require it — not a Phase 4.2 gate |

MVP constraints:

- Single active published version per document remains source of truth for BM25 membership.  
- Chunk id alignment with dense datapoint ids where possible for fusion keys.  
- Multi-instance Cloud Run: each instance builds/reloads index (acceptable at MVP scale; document consistency lag).

### 5. Citation UX (consequence / later 4.x polish)

Prefer **dedupe by `document_id`** (or max-score chunk per doc) when packing citations for the UI, so list answers are not dominated by near-duplicate chunks from one file. May land after hybrid if metrics show citation noise still high — not blocked by eval harness.

### 6. Implementation phasing

| Step | Scope |
|------|--------|
| **4.0** | This ADR (Accepted) |
| **4.1** | Eval harness + golden set + **dense-only baseline** metrics report |
| **4.2** | Hybrid MVP: in-process BM25 + RRF inside LangGraph retrieve; flag + tests; re-run eval vs baseline |
| **4.x later** | Citation dedupe polish; OpenSearch optional; multi-turn / ACL depth / fuller guards (separate backlog items) |

### 7. Explicitly out of scope (this ADR)

- Full agentic multi-tool loops  
- Voice / STT / TTS  
- Replacing Vertex Vector Search  
- Skipping evaluation and “tuning by feel”  

## Rationale

| Criterion | Why |
|-----------|-----|
| Eval first | Prevents unmeasured “improvements”; matches enterprise quality gates |
| Hybrid + RRF | Industry-standard fix for dense lexical misses without abandoning Vector Search |
| Extend retrieve node | Minimal surface area; preserves Phase 3 API contracts |
| In-process BM25 first | Fastest path to measured gain at current corpus scale; no new managed service |
| Golden set with list + refusal | Targets observed production failures, not only generic QA |

## Consequences

### Positive

- Clear Phase 4.1 / 4.2 work split and acceptance criteria  
- Measurable Recall@k and list-completeness before/after hybrid  
- Dense path remains fallback; Vector Search investment retained  
- Aligns ADR-0008 deferred hybrid with a concrete design  

### Negative / Trade-offs

- In-process BM25 memory and reload complexity on multi-instance Cloud Run  
- RRF may need tuning (\(k\), per-channel top_n)  
- Golden-set maintenance cost  
- Faithfulness scoring is approximate until stronger judges land  

### Risks and Mitigations

- **Risk:** Hybrid ships without beating baseline  
  - **Mitigation:** Gate default-on hybrid on eval report (4.2 acceptance)  
- **Risk:** BM25 index stale after publish  
  - **Mitigation:** Reload hook on publish/retire; readiness check / rebuild endpoint for ops  
- **Risk:** Eval set leaks into training-like prompt tuning  
  - **Mitigation:** Held-out golden only; no fine-tune on golden answers  
- **Risk:** Citation spam from multi-chunk same doc  
  - **Mitigation:** 4.x document_id dedupe polish  

## Alternatives Rejected

### Dense-only forever

- Why rejected: Live failures on headings/tables/lists are structural to pure dense; product needs hybrid.

### Replace Vector Search with BM25-only or a single new store

- Why rejected: Dense already works for semantic queries; dual channel + RRF is lower risk than a full re-platform.

### Skip evaluation; ship hybrid by anecdote

- Why rejected: Violates measurable quality gates and Phase 0 non-negotiables for ML systems.

### New product surface / separate hybrid API

- Why rejected: Extra client complexity; LangGraph retrieve extension keeps one answer path.

### Managed OpenSearch as day-one BM25

- Why rejected: Ops and cost premature for current scale; in-process MVP first, OpenSearch if needed later.

## References

- [ADR-0007 Embedding and Vector Search](./0007-embedding-and-vector-search.md)  
- [ADR-0008 Retrieval and Grounded Generation](./0008-retrieval-and-grounded-generation.md)  
- [ADR-0004 Guardrails Architecture](./0004-guardrails-architecture.md)  
- [architecture/overview.md](../architecture/overview.md) §5 LangGraph  
- Backlog: BL-RAG-01, BL-RAG-02, BL-RAG-17, BL-ANL-03 (eval themes)  
