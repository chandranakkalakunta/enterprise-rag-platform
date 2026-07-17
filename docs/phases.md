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
| **2.0** | ADR-0006 Metadata store | ✅ **Accepted** | [Firestore Native](./adr/0006-metadata-store-firestore.md) |
| **2** | Ingestion & Versioning | 🔜 **Next** | Upload, parse, version publish/retire, ingest-worker |
| **3** | Hybrid RAG + Guardrails | Planned | LangGraph path, citations, feedback, metadata filters |
| **4** | Multi-turn & ACL depth | Planned | Conversations, collections, safety tuning |
| **5** | Voice + PWA | Planned | STT/TTS, installable shell |
| **6** | Analytics & Evaluation (+ Binary Auth hardening) | Planned | BigQuery; NFR-SEC-14 / BL-SEC-09 |

## Phase 0 closure links

- Retrospective: [docs/retrospectives/phase-0.md](./retrospectives/phase-0.md)
- Engineering report: [docs/reports/phase-0-engineering-report.md](./reports/phase-0-engineering-report.md)

## Phase 1 closure links

- Retrospective: [docs/retrospectives/phase-1.md](./retrospectives/phase-1.md)
- Engineering report: [docs/reports/phase-1-engineering-report.md](./reports/phase-1-engineering-report.md)
- Backlog: [docs/backlog.md](./backlog.md)
- Protocol: [docs/grok-three-agent-protocol.md](./grok-three-agent-protocol.md)

Last updated: 2026-07-17
