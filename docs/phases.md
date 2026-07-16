# Phase Index — Enterprise RAG Platform

Living index of delivery phases and status.  
Update when a phase opens or closes.

| Phase | Name | Status | Primary artifacts |
|-------|------|--------|-------------------|
| **0** | Foundation & Requirements Lock | ✅ **Complete** — [PR #1](https://github.com/chandranakkalakunta/enterprise-rag-platform/pull/1) | [requirements](./requirements.md) · [ui-specs](./ui-specs.md) · [architecture](./architecture/overview.md) · [ADRs](./adr/) · [retro](./retrospectives/phase-0.md) · [report](./reports/phase-0-engineering-report.md) |
| **1** | GCP Foundation | 🔜 Next | APIs, CMEK, SAs, WIF, health version fields, three Cloud Run services, OAuth allowlist |
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

Last updated: 2026-07-16
