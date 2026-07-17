# Phase Index — Enterprise RAG Platform

Living index of delivery phases and status.  
Update when a phase opens or closes.

| Phase | Name | Status | Primary artifacts |
|-------|------|--------|-------------------|
| **0** | Foundation & Requirements Lock | ✅ **Complete** — [PR #1](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/1) | [requirements](./requirements.md) · [ui-specs](./ui-specs.md) · [architecture](./architecture/overview.md) · [ADRs](./adr/) · [retro](./retrospectives/phase-0.md) · [report](./reports/phase-0-engineering-report.md) |
| **0.1** | GCP project ID switch | ✅ **Complete** | Example/default `enterprise-rag-platform-502711` |
| **1.1** | Multi-env Terraform + APIs + state buckets | ✅ **Complete** | [bootstrap runbook](./runbooks/terraform-bootstrap.md) |
| **1.2** | Custom SAs + GitHub WIF | ✅ **Complete** | [WIF runbook](./runbooks/github-actions-wif.md) |
| **1.3** | CMEK + Secret Manager shells | ✅ **Complete** | [CMEK runbook](./runbooks/secret-manager-cmek.md) |
| **1.4** | Application GCS buckets with CMEK | ✅ **Complete** | [GCS runbook](./runbooks/gcs-document-buckets.md) |
| **1.5** | Health endpoints + CI storage.admin removal | ✅ **Complete** | NFR-REL-03a; BL-FND-24 |
| **1.6** | Cloud Run stubs + OAuth allowlist prep | ✅ **Complete** | [Cloud Run](./runbooks/cloud-run-services.md) · [OAuth](./runbooks/oauth-domain-allowlist.md) |
| **1.7** | CI skeleton (GHA + WIF) | ✅ **Applied** | [CI runbook](./runbooks/github-actions-ci.md) |
| **2+** | Auth, RAG features | 🔜 Next | Binary Auth Phase 6+ (NFR-SEC-14) |
| **2** | Ingestion & Versioning | Planned | Upload, parse, version publish/retire, ingest-worker |
| **3** | Hybrid RAG + Guardrails | Planned | LangGraph path, citations, feedback, metadata filters |
| **4** | Multi-turn & ACL depth | Planned | Conversations, collections, safety tuning |
| **5** | Voice + PWA | Planned | STT/TTS, installable shell |
| **6** | Analytics & Evaluation | Planned | BigQuery dashboards, held-out quality gates |

## Phase 0 closure links

- Retrospective: [docs/retrospectives/phase-0.md](./retrospectives/phase-0.md)
- Engineering report: [docs/reports/phase-0-engineering-report.md](./reports/phase-0-engineering-report.md)
- Backlog: [docs/backlog.md](./backlog.md)
- Protocol: [docs/grok-three-agent-protocol.md](./grok-three-agent-protocol.md)

Last updated: 2026-07-17
