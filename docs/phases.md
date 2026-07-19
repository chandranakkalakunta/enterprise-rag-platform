# Phase Index — Enterprise RAG Platform

Living index of delivery phases and status.  
Update when a phase opens or closes.

| Phase | Name | Status | Primary artifacts |
|-------|------|--------|-------------------|
| **0** | Foundation & Requirements Lock | ✅ **Complete** — [PR #1](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/1) | [requirements](./requirements.md) · [ui-specs](./ui-specs.md) · [architecture](./architecture/overview.md) · [ADRs](./adr/) · [retro](./retrospectives/phase-0.md) · [report](./reports/phase-0-engineering-report.md) |
| **0.1** | GCP project ID switch | ✅ **Complete** — [PR #2](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/2) | `var.gcp_project_id` = `enterprise-rag-platform-502711` |
| **1** | **GCP Foundation** | ✅ **Complete** — PRs [#3](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/3)–[#9](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/9) | [retro](./retrospectives/phase-1.md) · [eng report](./reports/phase-1-engineering-report.md) |
| **1.1** | Multi-env Terraform + APIs + state buckets | ✅ **Complete** — PR #3 | [bootstrap runbook](./runbooks/terraform-bootstrap.md) |
| **1.2** | Custom SAs + GitHub WIF | ✅ **Complete** — PR #4 | [WIF runbook](./runbooks/github-actions-wif.md) |
| **1.3** | CMEK + Secret Manager shells | ✅ **Complete** — PR #5 | [CMEK runbook](./runbooks/secret-manager-cmek.md) |
| **1.4** | Application GCS buckets with CMEK | ✅ **Complete** — PR #6 | [GCS runbook](./runbooks/gcs-document-buckets.md) |
| **1.5** | Health endpoints + CI storage.admin removal | ✅ **Complete** — PR #7 | NFR-REL-03a; BL-FND-24 |
| **1.6** | Cloud Run stubs + OAuth allowlist prep | ✅ **Complete** — PR #8 | [Cloud Run](./runbooks/cloud-run-services.md) · [OAuth](./runbooks/oauth-domain-allowlist.md) |
| **1.7** | CI skeleton (GHA + WIF) | ✅ **Complete** — PR #9 | [CI runbook](./runbooks/github-actions-ci.md) |
| **2** | **Ingestion & Versioning (MVP)** | ✅ **Complete** — PRs [#11](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/11)–[#15](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/15) | [retro](./retrospectives/phase-2.md) · [eng report](./reports/phase-2-engineering-report.md) |
| **2.0** | ADR-0006 Metadata store | ✅ **Accepted** | [Firestore Native](./adr/0006-metadata-store-firestore.md) |
| **2.1** | Upload API + GCS write + Firestore | ✅ **Complete** | [Upload runbook](./runbooks/document-upload-api.md) |
| **2.2** | Firestore DB + text extraction + status | ✅ **Complete** | [Firestore](./runbooks/firestore-metadata.md) |
| **2.3** | Chunking + processed/ storage + CR lifecycle | ✅ **Complete** | processed/full.txt + chunks.jsonl |
| **2.4** | Publish + retire version lifecycle | ✅ **Complete** | [Lifecycle runbook](./runbooks/version-lifecycle.md) |
| **3** | **Retrieval Foundation + grounded Q&A (MVP)** | ✅ **Complete** — PRs [#17](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/17)–[#22](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/22) | [retro](./retrospectives/phase-3.md) · [eng report](./reports/phase-3-engineering-report.md) |
| **3.0** | ADR-0007 + ADR-0008 | ✅ **Accepted** | [Embeddings/VS](./adr/0007-embedding-and-vector-search.md) · [Retrieval/gen](./adr/0008-retrieval-and-grounded-generation.md) |
| **3.1** | Embedding pipeline on ready | ✅ **Complete** | `embeddings.jsonl` + `embeddings_status` |
| **3.2** | Vector Search upsert + activate/deactivate | ✅ **Complete** | [vector-search runbook](./runbooks/vector-search.md) |
| **3.2h** | Bootstrap datapoint.json hotfix | ✅ **Complete** | Never `.keep` under `contents_delta_uri` |
| **3.3** | Dense Search API | ✅ **Complete** | [dense-search runbook](./runbooks/dense-search-api.md) |
| **3.4** | Grounded Answer API (LangGraph + Gemini) | ✅ **Complete** | [grounded-answer runbook](./runbooks/grounded-answer-api.md) |
| **5** | Voice + **full PWA** | ✅ **Complete** | [retro](./retrospectives/phase-5.md) · [eng report](./reports/phase-5-engineering-report.md) |
| **5.0** | ADR-0009 Auth/Roles + ADR-0010 PWA shell & version reload | ✅ **Accepted** | [Auth](./adr/0009-authn-authz-user-profiles.md) · [PWA/reload](./adr/0010-pwa-shell-version-reload.md) |
| **5.1** | OAuth + `/me` + app shell + version watcher | ✅ **Complete** | [Auth runbook](./runbooks/oauth-and-frontend-auth.md) |
| **5.2** | Chat UI — answer, refusal, citations | ✅ **Complete** | ChatPanel → `POST /api/v1/query/answer` |
| **5.3** | Admin UI + chat ↑ / `/clear` | ✅ **Complete** | Upload/list/publish/retire; GET documents |
| **5.4** | PWA install + closeout polish | ✅ **Complete** | [PWA runbook](./runbooks/pwa-install.md) |
| **4** | **RAG quality** (eval + hybrid + multi-turn/ACL later) | 🔄 **In progress** | Starts with ADR-0011 |
| **4.0** | ADR-0011 Eval + Hybrid retrieval design | ✅ **Accepted** | [ADR-0011](./adr/0011-rag-evaluation-and-hybrid-retrieval.md) |
| **4.1** | Eval harness + golden set + dense baseline | ✅ **Complete** | [eval runbook](./runbooks/rag-eval-harness.md) · [baseline](./eval/baseline-dense.md) |
| **4.2** | Hybrid MVP (in-process BM25 + RRF in LangGraph retrieve) | 🔜 **Next** | After 4.1 merge |
| **6** | Analytics & Evaluation ops (+ Binary Auth / LB hardening) | Planned | BigQuery; NFR-SEC-14; HTTPS LB + Cloud Armor |

## Delivery order (Coordinator — post–Phase 3)

Phase **numbers** are stable product tracks. **Execution order after Phase 3:**

1. **Phase 5** — full responsive PWA / UI — ✅ **Complete**  
2. **Phase 4** — RAG quality (eval → hybrid BM25+RRF → multi-turn/ACL/guards) — **started 4.0**  
3. **Phase 6** — analytics / eval / Binary Auth / **HTTPS LB + Cloud Armor**  

## Phase 0–2 closure links

- Phase 0: [retro](./retrospectives/phase-0.md) · [report](./reports/phase-0-engineering-report.md)  
- Phase 1: [retro](./retrospectives/phase-1.md) · [report](./reports/phase-1-engineering-report.md)  
- Phase 2: [retro](./retrospectives/phase-2.md) · [report](./reports/phase-2-engineering-report.md)  

## Phase 3 closure links

- Retrospective: [docs/retrospectives/phase-3.md](./retrospectives/phase-3.md)  
- Engineering report: [docs/reports/phase-3-engineering-report.md](./reports/phase-3-engineering-report.md)  
- Backlog: [docs/backlog.md](./backlog.md) (hybrid / cache / guards / hard-delete remain open)  
- Protocol: [docs/grok-three-agent-protocol.md](./grok-three-agent-protocol.md)  

## Phase 5 scope note

Phase 5 delivers a **full Progressive Web App**: responsive on **desktop, tablet, and mobile browsers**, plus **installable** PWA shell (and optional voice). **Native App Store / Play Store apps are out of scope.**

### Phase 5.0 decision links

- [ADR-0009 AuthN/AuthZ + Firestore user profiles](./adr/0009-authn-authz-user-profiles.md) — Google OAuth; domain allowlist; roles `viewer` / `content_admin` / `admin`; `ADMIN_EMAILS` bootstrap  
- [ADR-0010 PWA shell + backend version auto-reload](./adr/0010-pwa-shell-version-reload.md) — poll `/health`; reload on `version` / `deployed_at` change; LB deferred  

### Phase 5.1 implementation links

- [oauth-and-frontend-auth runbook](./runbooks/oauth-and-frontend-auth.md) — Coordinator OAuth client, secrets, `ADMIN_EMAILS`, local run  
- Backend: Google ID token verify · domain gate · Firestore `users/{uid}` · `GET /api/v1/me` · role gates on APIs  
- Frontend: Next.js shell · GIS login · Chat home · Admin nav by role · health version watcher · manifest placeholder  

### Phase 5.2 implementation links

- Chat: composer + message list; `postAnswer` → existing answer API; refusal + citation rendering  
- Keyboard: **Enter** send, **Shift+Enter** newline  
- Manual checklist: [frontend/README.md](../frontend/README.md)  

### Phase 5.3 implementation links

- Admin: upload PDF/MD; document list; publish/retire with confirm  
- Backend reads: `GET /api/v1/documents`, `GET /api/v1/documents/{document_id}` (content_admin|admin)  
- Chat: **↑** cycles previous user prompts; **`/clear`** clears local history  

### Phase 5.4 + closure

- [PWA install runbook](./runbooks/pwa-install.md) — manifest, SW, shell offline only  
- Citation title fallback; upload title defaults to filename; `GENERATION_MODEL_ID` default `gemini-2.5-flash`  
- Closure: [retro](./retrospectives/phase-5.md) · [eng report](./reports/phase-5-engineering-report.md)  

### Phase 4.0 decision links

- [ADR-0011 RAG evaluation + hybrid retrieval](./adr/0011-rag-evaluation-and-hybrid-retrieval.md) — eval first; BM25 + dense + RRF inside LangGraph `retrieve`; in-process BM25 MVP then optional OpenSearch  
- Order: **4.1** eval harness + dense baseline → **4.2** hybrid MVP  

### Phase 4.1 implementation links

- Golden set: `eval/golden/golden_set.jsonl` (25 cases)  
- Harness: `python -m eval.harness` (fixture | live)  
- Baseline notes: [docs/eval/baseline-dense.md](./eval/baseline-dense.md)  
- Runbook: [rag-eval-harness.md](./runbooks/rag-eval-harness.md)  

Last updated: 2026-07-19 (Phase 4.1 eval harness)
