# Runbook: Citation dedupe + BM25 warm-start (Phase 4.3)

## Citation SOURCES dedupe

| Setting | Default | Effect |
|---------|---------|--------|
| `CITATION_MAX_PER_DOC` | `1` | Max source cards per `document_id` in `/query/answer` |
| `CITATION_MERGE_SNIPPETS` | `true` | When max=1, append one extra distinct snippet (` \| `) onto the best-scoring card |

- Generation still uses **all** retrieved chunks; only the **citations** array is deduped.
- Frontend also dedupes by `document_id` as a safety net (`dedupeCitationsByDocument`).

## BM25 warm-start

On API process start (background daemon thread):

1. If `BM25_WARM_START=true` and hybrid (or `BM25_ALWAYS_INDEX`) is on  
2. Scan Firestore documents with `active_version_id` set and version `status=published`  
3. Load each version’s `chunks.jsonl` from GCS  
4. Rebuild in-process BM25 index  

Failures are **logged only** — the API still becomes ready.

| Setting | Default |
|---------|---------|
| `BM25_WARM_START` | `true` |
| `BM25_WARM_START_MAX_DOCS` | `200` |

Publish/retire still incrementally update the index (Phase 4.2).

### Operator notes

- Multi-instance Cloud Run: **each** instance warms its own memory index.  
- After cold deploy, hybrid lexical quality improves once warm-start finishes (seconds–minutes depending on corpus).  
- Check logs for `bm25_warm_start_complete` / `bm25_warm_start_failed`.  
- Disable with `BM25_WARM_START=false` if startup GCS/Firestore load is undesirable in a given env.

## Related

- [ADR-0011](../adr/0011-rag-evaluation-and-hybrid-retrieval.md)  
- Hybrid search (Phase 4.2)  
