# Runbook: Version publish / retire lifecycle (Phase 2.4)

**ADR:** [ADR-0003 Document Versioning](../adr/0003-document-versioning.md)  
**Service:** `rag-api`  
**Auth:** Temporary Bearer / `AUTH_DEV_BYPASS` (same as upload; `content_admin` later)

## Endpoints

| Method | Path | Action |
|--------|------|--------|
| `POST` | `/api/v1/documents/{document_id}/versions/{version_id}/publish` | Publish ready version |
| `POST` | `/api/v1/documents/{document_id}/versions/{version_id}/retire` | Retire ready or published version |

No request body required.

## State machine (Phase 2.4)

```text
processing → ready | failed     (Phase 2.2–2.3 upload path)
ready      → published          (publish)
ready      → retired            (retire without publishing)
published  → retired            (retire or superseded by new publish)
```

| From | To | Operation |
|------|-----|-----------|
| `ready` | `published` | publish |
| `ready` | `retired` | retire |
| `published` | `retired` | retire **or** automatic on new publish |

**Illegal** (HTTP **409**): publish from `processing` / `failed` / `published` / `retired`; retire from `processing` / `failed` / `retired`.

**Not found** (HTTP **404**): missing document or version.

**Bad IDs** (HTTP **400**): empty or path-like `document_id` / `version_id`.

## Publish semantics

Atomic Firestore transaction:

1. Load document + version (must be `ready`).
2. Set version `status=published`, `published_at`, `published_by`.
3. Set `document.active_version_id = version_id`.
4. If another version was active and `status=published`, set it to `retired` with `retired_at` / `retired_by`.
5. **Never delete** version records.

### Response `200`

```json
{
  "document_id": "…",
  "version_id": "…",
  "status": "published",
  "active_version_id": "…",
  "published_at": "2026-07-17T12:00:00Z",
  "published_by": "dev-bypass",
  "retired_at": null,
  "retired_by": null,
  "previous_published_version_id": "… or null",
  "cleared_active_pointer": false
}
```

## Retire semantics

Atomic Firestore transaction:

1. Load document + version (must be `ready` or `published`).
2. Set version `status=retired`, `retired_at`, `retired_by`.
3. If `document.active_version_id == version_id`, set `active_version_id = null`.
4. History retained.

### Response `200`

```json
{
  "document_id": "…",
  "version_id": "…",
  "status": "retired",
  "active_version_id": null,
  "cleared_active_pointer": true,
  "retired_at": "…",
  "retired_by": "dev-bypass"
}
```

## Example curl

```bash
export API=http://localhost:8000
# After upload returned document_id / version_id with status=ready:

curl -sS -X POST "$API/api/v1/documents/$DOC_ID/versions/$VER_ID/publish" | jq .
curl -sS -X POST "$API/api/v1/documents/$DOC_ID/versions/$VER_ID/retire" | jq .
```

## Implementation notes

- Domain rules: `app/services/lifecycle_rules.py` (pure, unit-tested).
- Transactions: `app/services/lifecycle.py` (`@firestore.transactional`).
- Index alias swap on publish (BM25/vector) is **not** implemented yet (BL-ING-06 / Phase 3).
- Retrieval should use `active_version_id` only when wiring query path.

## Related

- [Document upload API](./document-upload-api.md)
- [Firestore metadata](./firestore-metadata.md)
