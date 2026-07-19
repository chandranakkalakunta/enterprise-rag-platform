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
| **3** | Retrieval Foundation + grounded Q&A | ✅ **MVP Complete** (3.0–3.4) | Dense path; hybrid deferred |
| **3.0** | ADR-0007 + ADR-0008 | ✅ **Accepted** | [Embeddings/VS](./adr/0007-embedding-and-vector-search.md) · [Retrieval/gen](./adr/0008-retrieval-and-grounded-generation.md) |
| **3.1** | Embedding pipeline on ready | ✅ **Complete** | `embeddings.jsonl` + `embeddings_status` |
| **3.2** | Vector Search upsert + activate/deactivate | ✅ **Complete** | [vector-search runbook](./runbooks/vector-search.md) |
| **3.3** | Dense Search API | ✅ **Complete** | [dense-search runbook](./runbooks/dense-search-api.md) |
| **3.4** | Grounded Answer API (LangGraph + Gemini) | ✅ **Complete** | [grounded-answer runbook](./runbooks/grounded-answer-api.md) |
| **4** | Multi-turn & ACL depth (+ hybrid/RRF stretch) | Planned | Conversations, collections, safety tuning |
| **5** | Voice + **full PWA** | Planned | Desktop/tablet/mobile browser + installable PWA; **no native apps** |
| **6** | Analytics & Evaluation (+ Binary Auth hardening) | Planned | BigQuery; NFR-SEC-14 / BL-SEC-09 |

## Phase 0 closure links

- Retrospective: [docs/retrospectives/phase-0.md](./retrospectives/phase-0.md)
- Engineering report: [docs/reports/phase-0-engineering-report.md](./reports/phase-0-engineering-report.md)

## Phase 1 closure links

- Retrospective: [docs/retrospectives/phase-1.md](./retrospectives/phase-1.md)
- Engineering report: [docs/reports/phase-1-engineering-report.md](./reports/phase-1-engineering-report.md)

## Phase 2 closure links

- Retrospective: [docs/retrospectives/phase-2.md](./retrospectives/phase-2.md)
- Engineering report: [docs/reports/phase-2-engineering-report.md](./reports/phase-2-engineering-report.md)
- Backlog: [docs/backlog.md](./backlog.md) (worker / job visibility / real auth moved out of Phase 2)
- Protocol: [docs/grok-three-agent-protocol.md](./grok-three-agent-protocol.md)

## Phase 3.0 decision links

- [ADR-0007 Embedding & Vector Search](./adr/0007-embedding-and-vector-search.md) — Vertex embeddings; embed on ready; activate on publish  
- [ADR-0008 Retrieval & Grounded Generation](./adr/0008-retrieval-and-grounded-generation.md) — LangGraph MVP; dense retrieve; Gemini; top_k=5; temp=0.2  

## Phase 5 scope note

Phase 5 delivers a **full Progressive Web App**: responsive on **desktop, tablet, and mobile browsers**, plus **installable** PWA shell (and optional voice). **Native App Store / Play Store apps are out of scope.**

Last updated: 2026-07-18 (Phase 3.1 embedding pipeline)
