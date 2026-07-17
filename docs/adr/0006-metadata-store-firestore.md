# ADR-0006: Metadata Store — Firestore (Native Mode)

## Status

Accepted — 2026-07-17

## Context

The Enterprise RAG Platform needs a durable **metadata store** for:

- Document entities (title, collection, ACL labels, audit fields)
- **Version state machine** (draft → processing → ready → published → retired) per [ADR-0003](./0003-document-versioning.md)
- Ingest job status and error summaries
- Pointers to GCS object keys and index identifiers
- Session/feedback metadata as product features land

This was an open decision from Phase 0/1 (**BL-DEC-01**). Analytics remains planned on **BigQuery** (hashed IDs + metadata only — NFR-PRV-01). The store must fit a serverless Cloud Run stack, least-privilege IAM, and low operational overhead for a small team.

Forces:

1. Hierarchical document → version → job shape  
2. Frequent point reads/writes by id (publish, job updates)  
3. Avoid idle cost and instance management  
4. Analytical / reporting workload already assigned to BigQuery  
5. Long-term choice preferred before Phase 2 ingestion implementation  

## Decision

Use **Firestore (Native mode)** as the **long-term** metadata store for documents, versions, and ingest jobs.

- **Mode:** Native (not Datastore mode)  
- **Analytics / reporting:** BigQuery (unchanged)  
- **Binary/content storage:** GCS (`rag-docs-*`) with CMEK ([ADR-0005](./0005-security-posture.md) path)  
- **Access:** Application service accounts (`sa-rag-api`, `sa-rag-ingest`) with least-privilege roles; no client SDKs with broad project access  

## Rationale

| Criterion | How Firestore fits |
|-----------|-------------------|
| Data model | Hierarchical collections (documents → versions → jobs) map cleanly to collections/subcollections |
| Ops | Fully serverless; no connection pools, patching, or instance sizing |
| Cost | Pay-per-use; strong for early-to-medium metadata volume |
| Stack fit | Native with Cloud Run, IAM, and GCP serverless posture |
| Analytics | Complex queries and aggregates stay in BigQuery (already in architecture) |
| Velocity | Fast to implement for Phase 2 ingestion without standing up a SQL fleet |

Relational power (JOINs, multi-row ACID across arbitrary tables) is **not** required for the core metadata workload; the version state machine is entity-centric with clear keys.

## Consequences

### Positive

- Fast to implement and operate  
- Natural data model for the version state machine and job tracking  
- Pay-per-use cost model; scales automatically  
- Aligns with scale-to-zero Cloud Run economics  

### Negative / Trade-offs

- No SQL JOINs — denormalize where needed (e.g. active version summary on document)  
- Some complex queries must use BigQuery (export or dual-write analytics events), not Firestore  
- **1 MiB** document size limit (acceptable for metadata; content stays in GCS)  

### Risks and Mitigations

- **Risk:** Hot-spotting on high-write job documents  
  - **Mitigation:** Stable document IDs; avoid monotonically increasing keys under a single parent; batch job status updates carefully  
- **Risk:** Query limitations for admin listing  
  - **Mitigation:** Composite indexes for common list filters; push heavy analytics to BigQuery  
- **Risk:** Multi-document transactions limits  
  - **Mitigation:** Keep publish/atomic pointer updates within transaction limits (document + version pointers co-designed per ADR-0003)  

## Alternatives Rejected

### Cloud SQL (PostgreSQL)

- Why rejected: Higher operational burden (instances, connectivity, patching, pooling) and idle cost relative to metadata volume. Relational features are not required for core document/version/job paths.

### AlloyDB

- Why rejected: Same class of relational operational/cost trade-offs as Cloud SQL, amplified; overkill for hierarchical metadata when BigQuery covers analytics.

## References

- [ADR-0001 High-Level Architecture](./0001-high-level-architecture.md)  
- [ADR-0002 Tech Stack](./0002-tech-stack.md)  
- [ADR-0003 Document Versioning](./0003-document-versioning.md)  
- [Architecture overview](../architecture/overview.md)  
- [requirements.md](../requirements.md) (NFR-PRV-01, US-DOC-*, US-CA-*)  
- Backlog: BL-DEC-01  
