# Runbook: Document Upload API (Phase 2.1–2.3)

> **Publish / retire:** after status=`ready`, use [version-lifecycle.md](./version-lifecycle.md)  
> (`POST .../publish`, `POST .../retire`).

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

Pipeline: raw GCS → extract → chunk → processed GCS → Firestore final status.

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
  "chunk_count": 5,
  "processed_gcs_prefix": "processed/{document_id}/{version_id}/",
  "text_preview": "First ~500 characters…",
  "error_message": null
}
```

On extraction/chunking failure (still HTTP **201** — raw object + metadata exist):

```json
{
  "status": "failed",
  "error_message": "PDF extraction failed: ...",
  "chunk_count": 0,
  "processed_gcs_prefix": null,
  "text_preview": null
}
```

### Errors

| Status | When |
|--------|------|
| `400` | Unsupported media type, empty file, or file too large |
| `401` | Missing/invalid Bearer when `AUTH_DEV_BYPASS=false` |
| `500` | GCS or Firestore failure (safe message only) |

## Pipeline (Phase 2.3)

```text
validate → GCS raw/ → Firestore version status=processing
  → extract text (app.services.extraction)
  → chunk text (app.services.chunking; ~1000 chars, 150 overlap)
  → GCS processed/{doc}/{ver}/full.txt
  → GCS processed/{doc}/{ver}/chunks.jsonl
  → Firestore status=ready + pointers + text_preview
  → on failure: status=failed + error_message
  → return 201 with final status
```

| Type | Extractor |
|------|-----------|
| Markdown | UTF-8 decode + light markup strip |
| PDF | **pdfminer.six** |

- Extraction and chunking modules have **no** FastAPI / GCS / Firestore imports (worker-ready).
- **Full text is not stored in Firestore** (Phase 2.3). Only `text_preview` (~500 chars) + GCS URIs.

## Chunk defaults

| Parameter | Default | Notes |
|-----------|---------|--------|
| Target size | **1000** characters | Soft; prefers paragraph/sentence boundaries |
| Overlap | **150** characters | Previous tail re-included |
| Preview | **500** characters | Firestore `text_preview` |

Tuning (size, overlap, separators, evaluation): backlog **BL-ING-03b**.

### chunks.jsonl line shape

```json
{"chunk_id":"0","index":0,"text":"...","char_count":980,"start_offset":0,"end_offset":980}
```

### embeddings.jsonl line shape (Phase 3.1)

Written **after** content reaches `status=ready` (ADR-0007: embed on ready).

```json
{
  "chunk_id": "0",
  "index": 0,
  "embedding": [0.01, -0.02, "..."],
  "char_count": 980,
  "document_id": "...",
  "version_id": "..."
}
```

| Config | Default |
|--------|---------|
| `EMBEDDING_MODEL_ID` | `text-embedding-005` |
| `EMBEDDING_BATCH_SIZE` | `32` |
| `VERTEX_LOCATION` | `asia-south1` |

**Note:** Vector Search **upsert** is Phase **3.2**. This phase only persists the durable embedding artifact.

## GCS layout

```text
gs://{bucket}/raw/{document_id}/{version_id}/{filename}
gs://{bucket}/processed/{document_id}/{version_id}/full.txt
gs://{bucket}/processed/{document_id}/{version_id}/chunks.jsonl
gs://{bucket}/processed/{document_id}/{version_id}/embeddings.jsonl
```

CMEK via bucket default key `rag-gcs-key`.

## Firestore version fields (ready)

| Field | Purpose |
|-------|---------|
| `status` | Content lifecycle: `ready` \| `failed` (extract+chunk) |
| `gcs_uri` / `gcs_object_key` | Raw upload |
| `processed_gcs_prefix` | `processed/{doc}/{ver}/` |
| `full_text_gcs_uri` | Pointer to `full.txt` |
| `chunks_gcs_uri` | Pointer to `chunks.jsonl` |
| `chunk_count` | Number of chunks |
| `text_preview` | First ~500 chars |
| `extracted_char_count` | Full text length |
| `error_message` | When content `status=failed` |
| `embeddings_status` | **`ready` \| `failed`** (independent of content status) |
| `embedding_model_id` | Model used for this version |
| `embedded_chunk_count` | Vectors written |
| `embeddings_gcs_uri` | Pointer to `embeddings.jsonl` |
| `embeddings_error` | When embeddings_status=failed |

If extract+chunk succeed but Vertex embedding fails: **`status` remains `ready`**, `embeddings_status=failed` (text/chunks not corrupted).

**Removed from Firestore:** full `extracted_text` (legacy Phase 2.2 field deleted on ready/failed).

## Temporary auth (not production)

| Env | Behaviour |
|-----|-----------|
| `AUTH_DEV_BYPASS=true` (default) | No Bearer required |
| `AUTH_DEV_BYPASS=false` | Require `Authorization: Bearer $UPLOAD_BEARER_TOKEN` |

## Local tests

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt && pip check
pytest -q
```

## Local smoke (optional)

```bash
export GCP_PROJECT_ID=enterprise-rag-platform-502711
export GCS_DOCS_BUCKET=rag-docs-dev
export AUTH_DEV_BYPASS=true

cd backend && uvicorn app.main:app --reload --port 8000

curl -sS -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@./README.md;type=text/markdown" \
  -F "title=Backend README" | jq .

# Expect status=ready, chunk_count>=1, processed_gcs_prefix set
# Verify: gsutil cat gs://rag-docs-dev/processed/.../chunks.jsonl | head
```

## Residual risks / follow-ups

- Sync extract+chunk in API — move to ingest-worker for large PDFs
- Chunk defaults not evaluated on held-out corpus (BL-ING-03b)
- Embed/index not yet run on chunks
- Temp auth still not OAuth/`content_admin`

## Related

- [ADR-0003 Document Versioning](../adr/0003-document-versioning.md)
- [ADR-0006 Metadata Store — Firestore](../adr/0006-metadata-store-firestore.md)
- [GCS document buckets](./gcs-document-buckets.md)
- [Firestore metadata](./firestore-metadata.md)
