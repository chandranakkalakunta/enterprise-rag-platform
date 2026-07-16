# Issues Log — Enterprise RAG Platform

Record every non-trivial problem and the fix applied.  
Root-cause first; no silent workarounds (see protocol § root-cause).

| Date | Area | Problem | Root cause | Fix | Residual risk |
|------|------|---------|------------|-----|---------------|
| 2026-07-16 | Phase 0 | Empty workspace; no prior git history | Greenfield project | Full foundation scaffold on `phase-0-initialization` | Remote/PR depends on GitHub repo create |
| 2026-07-16 | Backend | `pip install -r requirements.txt` failed on default `python3` (3.14) | System default is 3.14; pinned pydantic-core builds against PyO3 max 3.13 | Use Python 3.12 per ADR-0002 (`python3.12 -m venv`); document in backend README | Local shells using bare `python3` may still hit 3.14 |

---

## Template for new entries

```
| YYYY-MM-DD | area | short problem | root cause | fix (PR/commit) | residual |
```
