# Runbook: Grounded Answer API (Phase 3.4)

**Endpoint:** `POST /api/v1/query/answer`  
**Service:** `rag-api`  
**ADR:** [ADR-0008](../adr/0008-retrieval-and-grounded-generation.md)

LangGraph pipeline: **retrieve (active-only) → evidence check → Gemini generate → citations**.

## Contract

### Request

```json
{
  "query": "How much annual leave do employees get?",
  "top_k": 5,
  "collection": "policies"
}
```

Same body as dense search (`query` required; `top_k`, `collection` optional).

### Success — grounded `200`

```json
{
  "query": "How much annual leave do employees get?",
  "answer": "Employees may take 20 days of leave per year [1].",
  "refused": false,
  "refusal_reason": null,
  "citations": [
    {
      "document_id": "…",
      "version_id": "…",
      "chunk_index": 0,
      "title": "Leave Policy",
      "filename": "leave.md",
      "snippet": "Employees may take 20 days…",
      "score": 0.91
    }
  ],
  "retrieval": {
    "top_k": 5,
    "hit_count": 3
  }
}
```

### Success — refused `200`

When evidence is insufficient:

```json
{
  "query": "…",
  "answer": "I do not have enough published evidence in the knowledge base…",
  "refused": true,
  "refusal_reason": "No published evidence was retrieved for this query.",
  "citations": [],
  "retrieval": { "top_k": 5, "hit_count": 0 }
}
```

### Errors

| Status | When |
|--------|------|
| `400` | Empty query |
| `422` | Missing body |
| `401` | Auth when bypass off |
| `503` | Retrieval or generation backend failure (safe message) |

## Refusal rules (MVP)

| Condition | Result |
|-----------|--------|
| Zero Vector Search hits | Refuse |
| Hits with no usable text | Refuse |
| Optional `EVIDENCE_MIN_SCORE` set and all scores below | Refuse |

No free-form invention without evidence.

## Pipeline

```text
POST /answer
  → LangGraph
       retrieve: dense_search (active=true, optional collection)
       evidence_check: pure gate
       generate_or_refuse: Gemini (temp default 0.2) or fixed refusal
  → answer + citations from hits
```

## Config

| Variable | Default | Notes |
|----------|---------|--------|
| `GENERATION_MODEL_ID` | `gemini-2.0-flash-001` | Vertex Gemini pin per env |
| `GENERATION_TEMPERATURE` | `0.2` | Low creativity |
| `RETRIEVAL_TOP_K` | `5` | Dense neighbors |
| `EVIDENCE_MIN_SCORE` | unset | Optional score floor |
| Vector Search env | required for live | Same as Phase 3.3 |

## Local tests

```bash
cd backend && pytest -q tests/test_answer_api.py tests/test_evidence.py
```

## Deferred

- Hybrid BM25 + RRF  
- Semantic cache  
- Full multi-layer guardrails (ADR-0004)  
- Multi-turn memory  

## Related

- [dense-search-api.md](./dense-search-api.md)  
- [vector-search.md](./vector-search.md)  
