# ADR-0008: Retrieval & Grounded Generation Flow

## Status

Accepted — 2026-07-18

## Context

With Phase 2 ingestion complete and [ADR-0007](./0007-embedding-and-vector-search.md) locking embeddings + Vector Search lifecycle, Phase 3 needs an explicit **query-time** contract:

- How is a user question turned into retrieved evidence?  
- How does generation stay **grounded** with **citations**?  
- What is in scope for the first shippable path vs deferred?

[ADR-0002](./0002-tech-stack.md) already chose **LangGraph** and **Vertex Gemini**. [ADR-0004](./0004-guardrails-architecture.md) describes a multi-layer guardrail stack; Phase 3 starts with a **minimal** evidence gate and expands later.

Forces:

1. Prefer **published/active** versions only (ADR-0003)  
2. Prefer **explicit, testable** orchestration over ad-hoc call chains  
3. Ship a thin vertical slice before hybrid fusion and full guardrails  
4. Configurable model IDs and knobs for env-specific pins  
5. Fail closed on insufficient evidence (no invented enterprise facts)  

## Decision

### Orchestration

Use **LangGraph** for query orchestration, starting with a **simple linear graph** (few nodes, clear edges). Expand nodes as hybrid retrieval and fuller guardrails land.

### MVP query flow

```text
user question
  → (optional auth context)
  → retrieve top_k dense neighbors from Vector Search
       · filter: published / active versions only
  → evidence check (minimal)
       · if insufficient evidence → refuse (no free invention)
  → generate with Vertex Gemini using retrieved chunks as context
  → return answer + citations (document_id, version_id, locator/chunk id)
```

| Step | Behavior |
|------|----------|
| Retrieve | Dense search via Vertex AI Vector Search; **`RETRIEVAL_TOP_K` default = 5** (configurable) |
| Scope | **Only currently published / active** versions (`active_version_id` / searchable set per ADR-0007) |
| Evidence check | Minimal: empty hits, all scores below threshold, or empty usable text → **refuse** with a safe message |
| Generate | Vertex **Gemini**; model via **`GENERATION_MODEL_ID`**; **`GENERATION_TEMPERATURE` default = 0.2** (configurable) |
| Citations | At least `document_id`, `version_id`, title if available, chunk/locator id |

Generation prompts must instruct the model to **use only provided evidence** and to support refusal when evidence is insufficient (policy aligned with ADR-0004 spirit; full multi-layer stack deferred).

### Configuration knobs

| Variable | Purpose | Default |
|----------|---------|---------|
| `GENERATION_MODEL_ID` | Vertex Gemini model id | Pin per env (e.g. flash-class GA id) |
| `GENERATION_TEMPERATURE` | Sampling temperature | **0.2** |
| `RETRIEVAL_TOP_K` | Dense neighbor count | **5** |
| `EMBEDDING_MODEL_ID` | Query embedding model | Same family as index (ADR-0007) |

### Deferred (explicitly not in initial Phase 3.x slice)

| Capability | Tracking |
|------------|----------|
| Hybrid **BM25 + dense** with **RRF** fusion | **Phase 4** — [ADR-0011](./0011-rag-evaluation-and-hybrid-retrieval.md); BL-RAG-01, BL-RAG-02 |
| Semantic cache | BL-RAG-11 / BL-DEC-06 |
| Full multi-layer guardrail stack | ADR-0004 expansion — BL-GRD-* |
| Multi-turn conversation memory | Phase 4 — BL-RAG-06 |
| ACL-deep collection filters (beyond published-only) | Phase 3–4 hardening — BL-RAG-05 |

Phase 0 stack still targets hybrid + RRF long-term; this ADR **narrows the first implementation** without reversing that product goal.

## Rationale

| Criterion | Why |
|-----------|-----|
| LangGraph | Explicit nodes, unit-testable edges, room to grow without rewrite |
| Dense-only first | Fastest path to grounded Q&A on published corpus |
| top_k = 5 | Enough context for short answers without excessive tokens/cost |
| temperature = 0.2 | Prefer faithful, low-creativity enterprise answers |
| Minimal refusal | Meets “no invent” for empty/weak evidence without blocking ship on full ADR-0004 |
| Published-only | Matches versioning MVP and audit expectations |

## Consequences

### Positive

- Clear Phase 3.1 implementation target  
- Config-driven models and knobs fit multi-env Terraform/Cloud Run  
- Citations and refuse path support product requirements (US-QA-*, US-EU-*)  

### Negative / Trade-offs

- Dense-only recall may miss exact keyword matches until hybrid lands  
- Minimal guards are weaker than full ADR-0004; residual risk of over-generation  
- Simple graph may need refactor when RRF and multi-turn arrive (acceptable)  

### Risks and Mitigations

- **Risk:** Model ignores context and hallucinates  
  - **Mitigation:** Prompt contract + evidence check + citations; expand output guards later  
- **Risk:** Retired content still retrieved  
  - **Mitigation:** Index deactivation on retire (ADR-0007) + automated tests  
- **Risk:** Config drift between embed and query models  
  - **Mitigation:** Same `EMBEDDING_MODEL_ID` for index build and query embed; document in runbook  

## Alternatives Rejected

### Ad-hoc retrieve-then-generate without LangGraph

- Why rejected: Harder to test and extend; contradicts ADR-0002.

### Hybrid BM25 + RRF in first slice

- Why rejected: Extra index path and fusion complexity; deferred deliberately to later 3.x / Phase 4.

### Always generate even with zero evidence

- Why rejected: Violates grounding / enterprise trust goals.

### High default temperature

- Why rejected: Encourages creative paraphrase over faithful citation for policy corpora.

## References

- [ADR-0001 High-Level Architecture](./0001-high-level-architecture.md)  
- [ADR-0002 Tech Stack](./0002-tech-stack.md)  
- [ADR-0003 Document Versioning](./0003-document-versioning.md)  
- [ADR-0004 Guardrails Architecture](./0004-guardrails-architecture.md)  
- [ADR-0006 Metadata Store — Firestore](./0006-metadata-store-firestore.md)  
- [ADR-0007 Embedding & Vector Search](./0007-embedding-and-vector-search.md)  
- [Architecture overview](../architecture/overview.md)  
- [requirements.md](../requirements.md) (US-QA-*, US-EU-*, NFR grounding)  
- Backlog: BL-RAG-01–05, BL-RAG-09, BL-RAG-12, BL-GRD-*, BL-DEC-06  
