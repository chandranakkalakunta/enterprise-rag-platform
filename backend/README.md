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
