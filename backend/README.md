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
OpenAPI: http://localhost:8000/docs

## Tests

```bash
cd backend
pytest -q
```

## Notes

- Dependencies are **pinned** in `requirements.txt` (CI installs only from this file).
- No secrets in code; use Secret Manager in deploy environments.
- See `docs/adr/0001-high-level-architecture.md` and `docs/adr/0002-tech-stack.md`.
