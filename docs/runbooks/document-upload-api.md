# Runbook: Document Upload API (Phase 2.1)

**Endpoint:** `POST /api/v1/documents/upload`  
**Service:** `rag-api`  
**Bucket (dev):** `gs://rag-docs-dev`  
**Metadata:** Firestore Native (`documents` + `versions` subcollection)

## Contract

### Request

- **Content-Type:** `multipart/form-data`
- **Fields:**
  | Field | Required | Description |
  |-------|----------|-------------|
  | `file` | Yes | PDF or Markdown file |
  | `title` | No | Document title (default stored as `Untitled`) |
  | `collection` | No | Collection label |

### Allowed types

| Content-Type | Extension |
|--------------|-----------|
| `application/pdf` | `.pdf` |
| `text/markdown` | `.md` / `.markdown` |
| `text/x-markdown` | `.md` / `.markdown` |

- Max size: **50 MB** (`MAX_UPLOAD_BYTES`)
- Empty files rejected

### Success — `201 Created`

```json
{
  "document_id": "uuid",
  "version_id": "uuid",
  "status": "processing",
  "gcs_uri": "gs://rag-docs-dev/raw/{document_id}/{version_id}/{filename}",
  "filename": "policy.pdf",
  "content_type": "application/pdf",
  "size_bytes": 12345,
  "title": "optional",
  "collection": "optional"
}
```

### Errors

| Status | When |
|--------|------|
| `400` | Unsupported media type, empty file, or file too large |
| `401` | Missing/invalid Bearer when `AUTH_DEV_BYPASS=false` |
| `500` | GCS or Firestore failure (safe message only) |

## GCS path convention

```text
gs://{GCS_DOCS_BUCKET}/raw/{document_id}/{version_id}/{safe_original_filename}
```

Example: `gs://rag-docs-dev/raw/a1b2.../c3d4.../handbook.pdf`

CMEK is enforced by the bucket default encryption key (`rag-gcs-key`).

## Firestore layout

```text
documents/{document_id}
  - document_id, title, collection
  - active_version_id: null (not published yet)
  - latest_version_id
  - created_at, updated_at, created_by

documents/{document_id}/versions/{version_id}
  - version_id, document_id
  - status: "processing"
  - gcs_uri, gcs_object_key, filename, content_type, size_bytes
  - created_at, created_by
```

Initial status is always **`processing`**. No parse/chunk/embed in Phase 2.1.

## Temporary auth (not production)

| Env | Behaviour |
|-----|-----------|
| `AUTH_DEV_BYPASS=true` (default) | No Bearer required |
| `AUTH_DEV_BYPASS=false` | Require `Authorization: Bearer $UPLOAD_BEARER_TOKEN` |

Full OAuth + `content_admin` role: later (BL-SEC-01 / BL-SEC-02).

## Local test (mocked path)

```bash
cd backend
source .venv/bin/activate
pytest -q tests/test_upload.py
```

## Local smoke against live API (optional)

Requires ADC with permission to write `rag-docs-dev` and Firestore:

```bash
export GCP_PROJECT_ID=enterprise-rag-platform-502711
export GCS_DOCS_BUCKET=rag-docs-dev
export AUTH_DEV_BYPASS=true
# Application Default Credentials: gcloud auth application-default login

uvicorn app.main:app --reload --port 8000

curl -sS -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@./README.md;type=text/markdown" \
  -F "title=Backend README" \
  -F "collection=internal" | jq .
```

OpenAPI UI: http://localhost:8000/docs

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `GCP_PROJECT_ID` | `enterprise-rag-platform-502711` | Project for GCS/Firestore clients |
| `GCS_DOCS_BUCKET` | `rag-docs-dev` | Target document bucket |
| `MAX_UPLOAD_BYTES` | `52428800` (50 MiB) | Size limit |
| `AUTH_DEV_BYPASS` | `true` | Skip Bearer check |
| `UPLOAD_BEARER_TOKEN` | empty | Shared secret when bypass off |

## Residual risks / follow-ups

- Firestore database + API enablement / IAM for `sa-rag-api` (e.g. `roles/datastore.user`) may still be needed before Cloud Run live upload works end-to-end.
- Orphan GCS objects if Firestore write fails after upload (cleanup tooling later).
- No parsing, chunking, or ingest-worker enqueue yet (Phase 2.2+).

## Related

- [ADR-0003 Document Versioning](../adr/0003-document-versioning.md)
- [ADR-0006 Metadata Store — Firestore](../adr/0006-metadata-store-firestore.md)
- [GCS document buckets](./gcs-document-buckets.md)
