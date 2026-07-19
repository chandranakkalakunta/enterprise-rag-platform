# Runbook: Dense Search API (Phase 3.3)

**Endpoint:** `POST /api/v1/query/search`  
**Service:** `rag-api`  
**ADR:** [ADR-0007](../adr/0007-embedding-and-vector-search.md) · [ADR-0008](../adr/0008-retrieval-and-grounded-generation.md)

Dense retrieval only — **no generation** (Gemini is Phase 3.4).

## Contract

### Request

```http
POST /api/v1/query/search
Content-Type: application/json
Authorization: Bearer …   # when AUTH_DEV_BYPASS=false
```

```json
{
  "query": "What is the leave policy?",
  "top_k": 5,
  "collection": "policies"
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `query` | Yes | Non-empty string (whitespace-only → 400) |
| `top_k` | No | Override `RETRIEVAL_TOP_K` (1–50; default **5**) |
| `collection` | No | Restrict namespace `collection` |

### Success — `200`

```json
{
  "query": "What is the leave policy?",
  "top_k": 5,
  "results": [
    {
      "text": "Employees may take…",
      "score": 0.91,
      "document_id": "…",
      "version_id": "…",
      "chunk_index": 0,
      "title": "Leave Policy",
      "filename": "leave.md",
      "collection": "policies",
      "datapoint_id": "{document_id}:{version_id}:{chunk_index}",
      "char_count": 120
    }
  ]
}
```

Empty corpus / no matches → `results: []` (still 200).

### Errors

| Status | When |
|--------|------|
| `400` | Invalid query / top_k |
| `401` | Auth required when bypass off |
| `422` | Missing body fields (Pydantic) |
| `503` | Embedding or Vector Search not configured / failed |

## Pipeline

```text
query → embed (EMBEDDING_MODEL_ID)
      → FindNeighbors (deployed index)
           restricts: active=true [+ collection]
           return_full_datapoint=true
      → map neighbors → results (no LLM)
```

**Always** filters `active=true` (published-only per ADR-0007).

## Environment

| Variable | Purpose |
|----------|---------|
| `VECTOR_SEARCH_ENABLED` | Must be `true` for live search |
| `VECTOR_SEARCH_ENDPOINT_ID` | Index endpoint id or full resource name |
| `VECTOR_SEARCH_DEPLOYED_INDEX_ID` | Deployed index id (e.g. `rag_docs_dev`) |
| `VECTOR_SEARCH_REGION` | Region (default `asia-south1`) |
| `VECTOR_SEARCH_PUBLIC_ENDPOINT_DOMAIN` | Optional public MatchService host |
| `RETRIEVAL_TOP_K` | Default **5** |
| `EMBEDDING_MODEL_ID` | Query embed model (same family as index) |

## Local test

```bash
cd backend && pytest -q tests/test_search_api.py
```

Live smoke (after publish with `active=true` datapoints):

```bash
curl -sS -X POST "$API/api/v1/query/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"leave policy","top_k":5}' | jq .
```

## Related

- [vector-search.md](./vector-search.md) — upsert / activate lifecycle  
- [version-lifecycle.md](./version-lifecycle.md) — publish sets active  
