# Runbook: Document Upload API (Phase 2.1–2.2)

**Endpoint:** `POST /api/v1/documents/upload`  
**Service:** `rag-api`  
**Bucket (dev):** `gs://rag-docs-dev`  
**Metadata:** Firestore Native (`(default)`, `asia-south1`) — `documents` + `versions` subcollection

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

Upload + GCS + Firestore + **synchronous text extraction**. Response includes the **final** status (`ready` or `failed`).

```json
{
  "document_id": "uuid",
  "version_id": "uuid",
  "status": "ready",
  "gcs_uri": "gs://rag-docs-dev/raw/{document_id}/{version_id}/{filename}",
  "filename": "policy.pdf",
  "content_type": "application/pdf",
  "size_bytes": 12345,
  "title": "optional",
  "collection": "optional",
  "extracted_char_count": 4200,
  "extracted_truncated": false,
  "error_message": null
}
```

On extraction failure (still HTTP **201** — object + metadata exist):

```json
{
  "status": "failed",
  "error_message": "PDF extraction failed: ...",
  "extracted_char_count": 0,
  "extracted_truncated": false
}
```

### Errors

| Status | When |
|--------|------|
| `400` | Unsupported media type, empty file, or file too large |
| `401` | Missing/invalid Bearer when `AUTH_DEV_BYPASS=false` |
| `500` | GCS or Firestore failure (safe message only) |

## Pipeline (Phase 2.2)

```text
validate → GCS raw/ → Firestore version status=processing
  → extract text (in-memory; module: app.services.extraction)
  → success: status=ready + extracted_text
  → failure: status=failed + error_message
  → return 201 with final status
```

| Type | Extractor |
|------|-----------|
| Markdown | UTF-8 decode + light markup strip |
| PDF | **pdfminer.six** |

- Extraction module has **no** FastAPI / GCS / Firestore imports (ready to move to ingest-worker).
- `extracted_text` is truncated at **400_000** chars for Firestore 1 MiB safety (`extracted_truncated=true` if cut).

## GCS path convention

```text
gs://{GCS_DOCS_BUCKET}/raw/{document_id}/{version_id}/{safe_original_filename}
```

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
  - status: processing → ready | failed
  - gcs_uri, gcs_object_key, filename, content_type, size_bytes
  - extracted_text, extracted_char_count, extracted_truncated
  - error_message (when failed)
  - extraction_completed_at, created_at, created_by
```

## Temporary auth (not production)

| Env | Behaviour |
|-----|-----------|
| `AUTH_DEV_BYPASS=true` (default) | No Bearer required |
| `AUTH_DEV_BYPASS=false` | Require `Authorization: Bearer $UPLOAD_BEARER_TOKEN` |

Full OAuth + `content_admin` role: later (BL-SEC-01 / BL-SEC-02).

## Local tests

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt && pip check
pytest -q
# extraction unit tests: pytest -q tests/test_extraction.py
```

## Local smoke against live API (optional)

Requires ADC with permission to write `rag-docs-dev` and Firestore (`roles/datastore.user` or broader):

```bash
export GCP_PROJECT_ID=enterprise-rag-platform-502711
export GCS_DOCS_BUCKET=rag-docs-dev
export AUTH_DEV_BYPASS=true
# gcloud auth application-default login

cd backend && uvicorn app.main:app --reload --port 8000

curl -sS -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@./README.md;type=text/markdown" \
  -F "title=Backend README" \
  -F "collection=internal" | jq .

# Expect status=ready and extracted_char_count > 0
```

### Verify Firestore record

```bash
# Console or gcloud (example with REST requires OAuth token)
# Path: projects/enterprise-rag-platform-502711/databases/(default)/documents/documents/{document_id}/versions/{version_id}
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

## Infrastructure (Phase 2.2)

| Resource | Value |
|----------|--------|
| Database | `(default)` Native mode |
| Location | `asia-south1` |
| API | `firestore.googleapis.com` |
| IAM | `roles/datastore.user` on `sa-rag-api`, `sa-rag-ingest` |

Terraform: `terraform/firestore.tf`. Apply with care — full `terraform apply` may also show Cloud Run image drift (CI-managed images). Prefer targeted apply for Firestore-only changes if needed.

## Residual risks / follow-ups

- Synchronous extraction in API will not scale for large PDFs — move to `rag-ingest` worker (Cloud Tasks/Pub/Sub, BL-DEC-05).
- Large `extracted_text` stored inline (truncated); later store full text under GCS `processed/` and keep pointer only.
- Orphan GCS objects if Firestore create fails after upload.
- Chunking / embed / publish not yet implemented.
- Terraform Cloud Run still references stub image — lifecycle/ignore or import CI-managed image to avoid accidental rollback on full apply.

## Related

- [ADR-0003 Document Versioning](../adr/0003-document-versioning.md)
- [ADR-0006 Metadata Store — Firestore](../adr/0006-metadata-store-firestore.md)
- [GCS document buckets](./gcs-document-buckets.md)
