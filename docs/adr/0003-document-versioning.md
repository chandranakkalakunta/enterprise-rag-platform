# ADR-0003: Document Versioning Model

## Status

Accepted — 2026-07-16

## Context

Enterprise RAG answers must be auditable: users and compliance need to know **which immutable snapshot** of a document supported a response. Content admins must publish updates without destroying history, and operators must re-index safely after pipeline fixes.

Forces:
- Retrieval must only use **active** versions by default.
- Publish must not expose half-built indexes (BM25 + vector consistency).
- Citations need stable version identifiers.
- GCS objects and metadata must align under CMEK and least privilege.

## Decision

### Version as immutable snapshot

- A **Document** is a logical entity (stable `document_id`, title, collection membership, ACL labels).
- A **Version** is an immutable content snapshot (`version_id`, parent `document_id`, content hash, created_by hash, timestamps).
- Binary content for each version is stored once in **GCS** under a version-bound object key. Overwrite-in-place of a published version’s bytes is forbidden.

### Lifecycle state machine

```text
DRAFT → PROCESSING → READY → PUBLISHED (active | inactive supersede)
                           ↘ FAILED
PUBLISHED → RETIRED
```

| State | Retrievable? | Notes |
|-------|--------------|-------|
| DRAFT | No | Upload recorded; processing not started or not finished |
| PROCESSING | No | Parse/chunk/embed/index in progress |
| READY | No | Indexes built in **staging**; awaiting publish |
| PUBLISHED | Yes if **active** | Exactly one active version per document (MVP rule) |
| RETIRED | No | History retained for audit |
| FAILED | No | Retry creates new processing attempt or new version per runbook |

**MVP rule:** one **active** published version per document. Prior published versions become inactive (still in history) when a new version is published, unless product later allows multi-active (would need new ADR).

### Atomic publish

Publish is a two-phase commit at the application level:

1. Ensure staging sparse + dense indexes for `version_id` are healthy.  
2. **Atomically** switch the document’s `active_version_id` (and index alias/namespace pointer) to the new version.  
3. Mark previous active version inactive (still PUBLISHED/inactive or transition label `SUPERSEDED` in metadata).

If step 1 fails, active pointer is unchanged.

### Citations

Every citation includes at least:

- `document_id`, `version_id` (and display label e.g. `v3`)  
- title  
- locator (page/heading/chunk id)  

### Re-index

Re-index of an existing `version_id` rebuilds staging indexes from immutable GCS bytes and swaps only when successful; content hash must still match stored hash or job fails.

### Retire

Retire removes the version from the active retrieval set and, if it was active, requires selecting another READY/PUBLISHED version or leaving document with no active version (queries skip it).

## Rationale

- Immutability enables audit and safe re-processing.  
- Staging + atomic pointer avoids dual-index drift (ADR-0001 risk).  
- Single active version keeps MVP reasoning simple for ACL and citations.  
- Aligns with user stories US-DOC-*, US-CA-*, US-EU-03.

## Consequences

### Positive
- Clear audit trail for “what was live”  
- Safer publishes  
- Re-index without rewriting history  

### Negative
- Storage growth with many versions (lifecycle policies later)  
- More complex admin UX (state machine)

### Risks and Mitigations
- **Risk:** Alias swap partial failure  
  - **Mitigation:** Single metadata transaction for active pointer; index alias update ordered and verified; fail closed  
- **Risk:** Large re-index cost  
  - **Mitigation:** Rate limits, budgets (NFR-COST-03)

## Alternatives Rejected

### Mutable “latest blob” without versions
- Why rejected: No auditability; breaks citation integrity

### Always multi-active versions in retrieval
- Why rejected: Ambiguous answers and higher ACL complexity for MVP

### Git-like branching model for documents
- Why rejected: Overkill for enterprise policy corpora

## References

- [ADR-0001](./0001-high-level-architecture.md)  
- [architecture/overview.md](../architecture/overview.md)  
- [requirements.md](../requirements.md) (US-DOC-*, US-CA-*)  
