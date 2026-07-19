# Backend — Enterprise RAG Platform

FastAPI service for query, ingestion, and admin APIs.

## Local development

```bash
cd backend
# ADR-0002: Python 3.12 required (do not use system python3 if it is 3.14+)
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip check
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health: http://localhost:8000/health  
Ready: http://localhost:8000/ready  
OpenAPI: http://localhost:8000/docs  
Upload: `POST /api/v1/documents/upload` (PDF/Markdown ≤50MB)

### Document upload (Phase 2.1–2.3)

Multipart form fields: `file` (required), `title`, `collection` (optional).

- Raw: `gs://$GCS_DOCS_BUCKET/raw/{document_id}/{version_id}/{filename}`
- Processed: `full.txt` + `chunks.jsonl` + **`embeddings.jsonl`** (Phase 3.1)
- Firestore: pointers + `text_preview`; **`embeddings_status`** separate from content `status`
- Default model: `EMBEDDING_MODEL_ID=text-embedding-005`
- Temp auth: `AUTH_DEV_BYPASS=true` (default) or Bearer `UPLOAD_BEARER_TOKEN`

See [docs/runbooks/document-upload-api.md](../docs/runbooks/document-upload-api.md).

### Version lifecycle (Phase 2.4)

- `POST /api/v1/documents/{document_id}/versions/{version_id}/publish` — ready → published; previous published auto-retired
- `POST /api/v1/documents/{document_id}/versions/{version_id}/retire` — ready|published → retired

See [docs/runbooks/version-lifecycle.md](../docs/runbooks/version-lifecycle.md).

### Dense search + grounded answer (Phase 3.3–3.4)

- `POST /api/v1/query/search` — top-k **active** chunks  
- `POST /api/v1/query/answer` — LangGraph retrieve → evidence → Gemini + citations  

See [dense-search](../docs/runbooks/dense-search-api.md) · [grounded-answer](../docs/runbooks/grounded-answer-api.md).

### Health contract (Phase 1.5)

Both `/health` (liveness) and `/ready` (readiness) return JSON:

```json
{
  "status": "ok",
  "service": "rag-api",
  "version": "dev",
  "deployed_at": ""
}
```

| Field | Source |
|-------|--------|
| `version` | `APP_VERSION` env (default `dev`) |
| `deployed_at` | `DEPLOYED_AT` env (default `""`; set ISO-8601 UTC at deploy) |

`/ready` also includes `"checks": {}` for future dependency probes.  
`/health` must not call external services.

## Tests

```bash
cd backend
pytest -q
```

## Notes

- Dependencies are **pinned** in `requirements.txt` (CI installs only from this file).
- No secrets in code; use Secret Manager in deploy environments.
- See `docs/adr/0001-high-level-architecture.md` and `docs/adr/0002-tech-stack.md`.
