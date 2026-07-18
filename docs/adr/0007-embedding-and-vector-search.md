# ADR-0007: Embedding Model & Vector Search Index

## Status

Accepted — 2026-07-18

## Context

Phase 2 delivered a complete MVP document lifecycle: upload → extract → chunk → GCS `processed/` → publish/retire, with Firestore metadata and a single `active_version_id` per document ([ADR-0003](./0003-document-versioning.md), [ADR-0006](./0006-metadata-store-firestore.md)).

Phase 3 must make **published** content retrievable. Open decisions **BL-DEC-02** (embedding model + dimensions) and **BL-DEC-03** (vector index topology / filter schema) must lock before implementation.

Forces:

1. Stay **GCP-native** and aligned with locked stack ([ADR-0002](./0002-tech-stack.md)): Vertex embeddings + Vertex AI Vector Search  
2. Index lifecycle must track **version state** (ready / published / retired) without dual sources of truth for chunk text  
3. Query path needs **chunk text at retrieval time** for grounded generation and citations  
4. Reprocessing (re-embed after model change) must re-read from **GCS**, not from a one-off cache  
5. Small-team ops: configurable model IDs, no hard-coded secrets or project-specific magic in application code  

## Decision

### Embedding provider and model

| Item | Choice |
|------|--------|
| Provider | **Vertex AI** |
| Model ID | Configurable via **`EMBEDDING_MODEL_ID`** (env / settings) |
| Target family | Latest **GA** Vertex **text** embedding model (e.g. `text-embedding-005` or the regional current GA equivalent at implement time) |
| Dimensions | Implementation detail derived from chosen model; stored/documented when index is created |
| Access | Runtime SAs (`sa-rag-api`, `sa-rag-ingest`) with least-privilege Vertex roles — no JSON keys |

Exact model ID is **pinned per environment** in config (not hard-coded in business logic). Changing model requires re-embed of corpus and typically a new index or full rebuild.

### Vector store

| Item | Choice |
|------|--------|
| Product | **Vertex AI Vector Search** (locked; not third-party ANN for MVP) |
| Datapoint identity | Stable id per chunk (e.g. `{document_id}:{version_id}:{chunk_index}`) |
| Payload / metadata | Store **chunk text** plus identifiers needed for citations and filters |
| Restricts / filters | At minimum: `document_id`, `version_id`, **active/published flag or version set** so queries only hit the active set |
| Index endpoint | Configurable (env / Terraform outputs) — implementation detail |

### Source of truth for chunk bytes

| Layer | Role |
|-------|------|
| **GCS `processed/{document_id}/{version_id}/chunks.jsonl`** | **Source of truth** for reprocessing, audit, and rebuild |
| **Vector Search datapoint** | Query-time retrieval: embedding + **chunk text in payload/metadata** |
| **Firestore** | Version status, `active_version_id`, GCS pointers — not full chunk bodies |

Query path **does not** re-fetch chunk text from GCS for each hit in the MVP (latency). GCS remains mandatory for re-index jobs.

### Index lifecycle (aligned with version state machine)

| Version event | Index action |
|---------------|--------------|
| Status becomes **`ready`** | **Embed** all chunks for that version; upsert datapoints into a **staging / non-active** set (or with `searchable=false` / version not in active filter) |
| **Publish** | **Activate** version in the searchable set (restricts / alias / active version filter so only this document’s active version is retrieved) |
| **Retire** | **Deactivate** / remove from active searchable set (history retained in GCS + Firestore; datapoints may remain non-searchable or be deleted per cost policy later) |

MVP rule (ADR-0003): **one active published version per document**. Publish of a new version retires the previous published version; index activation must follow that pointer.

Initial Phase 3 may implement embed + activate in the same job as long as **published-only** query filtering is correct; the lifecycle contract above remains the long-term rule.

### Configuration knobs

| Variable | Purpose | Default / notes |
|----------|---------|-----------------|
| `EMBEDDING_MODEL_ID` | Vertex text embedding model | Required at deploy; pin GA model id |
| `RETRIEVAL_TOP_K` | Neighbor count for dense retrieve | **5** (configurable) |
| Index endpoint / deployed index id | Vector Search endpoint | From Terraform / env |
| Embedding dimensions | Index schema | Tied to model; set at index create |

Related generation knobs are specified in [ADR-0008](./0008-retrieval-and-grounded-generation.md).

## Rationale

| Criterion | Why this choice |
|-----------|-----------------|
| Stack consistency | Matches ADR-0001 / ADR-0002 (Vertex + Vector Search) |
| IAM / residency | Same GCP project boundary as Cloud Run and GCS CMEK path |
| Ops | Managed ANN; no self-hosted vector DB |
| Lifecycle | Embed-on-ready avoids publish latency spikes; activate-on-publish keeps unpublished text out of answers |
| Grounding | Chunk text in datapoint payload enables citations without extra GCS round-trips |
| Rebuild | GCS `chunks.jsonl` allows full re-embed after model change |

## Consequences

### Positive

- Clear contract between Phase 2 artifacts and Phase 3 index  
- Published-only retrieval is enforceable with metadata filters  
- Configurable model IDs support regional GA upgrades without code rewrites  
- Reprocess path is well-defined (GCS → embed → upsert)  

### Negative / Trade-offs

- Dual storage of chunk text (GCS + index payload) — storage cost and consistency discipline  
- Model change implies corpus re-embed and careful cutover  
- Hybrid BM25 + RRF **not** in this ADR’s MVP path (deferred; see ADR-0008)  

### Risks and Mitigations

- **Risk:** Staging datapoints leak into production answers  
  - **Mitigation:** Query filters on active/published version only; integration tests on publish/retire  
- **Risk:** Payload size limits on Vector Search datapoints  
  - **Mitigation:** Chunk size already ~1000 chars (ADR Phase 2.3); truncate safely with pointer back to GCS if needed  
- **Risk:** Embed-on-ready cost for versions never published  
  - **Mitigation:** Accept for MVP latency-at-publish; optional later “embed on first publish only” would be a new ADR  

## Alternatives Rejected

### Third-party embeddings (OpenAI, Cohere, etc.)

- Why rejected: Extra vendor, data egress, weaker alignment with Vertex + Vector Search IAM and GCP non-negotiables for this project.

### Embed only on publish

- Why rejected: Couples long-running embed work to the publish API path; publish should stay a fast metadata/index-activation flip when possible. Embed-on-ready stages work earlier.

### Fetch chunk text from GCS at every query hit

- Why rejected: Extra latency and failure modes on the hot path. GCS remains source of truth for **rebuild**, not per-request text load.

### Self-hosted vector DB (e.g. pgvector, Weaviate)

- Why rejected for MVP: Operational burden; Vertex Vector Search already locked in ADR-0002.

## References

- [ADR-0001 High-Level Architecture](./0001-high-level-architecture.md)  
- [ADR-0002 Tech Stack](./0002-tech-stack.md)  
- [ADR-0003 Document Versioning](./0003-document-versioning.md)  
- [ADR-0006 Metadata Store — Firestore](./0006-metadata-store-firestore.md)  
- [ADR-0008 Retrieval & Grounded Generation](./0008-retrieval-and-grounded-generation.md)  
- [Architecture overview](../architecture/overview.md)  
- Backlog: BL-DEC-02, BL-DEC-03, BL-RAG-12, BL-ING-05, BL-ING-06  
