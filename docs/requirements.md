# Enterprise RAG Platform — Requirements

**Project:** enterprise-rag-platform  
**GCP project:** `sport-slot-dev`  
**Document version:** 1.0  
**Date:** 2026-07-16  
**Status:** Phase 0 baseline

---

## 1. Product Vision

A production-grade, GCP-native Enterprise RAG platform that lets authenticated users ask natural-language (and voice) questions over versioned enterprise documents and receive grounded answers with citations, guardrails, and privacy-safe analytics.

---

## 2. Personas

| Persona | Description |
|---------|-------------|
| **End User (Employee / Knowledge Worker)** | Asks questions; expects accurate, cited, fast answers |
| **Content Admin** | Uploads, versions, publishes, and retires documents |
| **Security / Compliance Officer** | Requires access control, auditability, no unnecessary PII retention |
| **Platform Operator** | Monitors latency, cost, quality, and incidents |
| **Product Owner** | Tracks usage analytics and answer quality trends |

---

## 3. User Stories

### 3.1 Authentication & Access

| ID | Story | Priority | Phase (target) |
|----|-------|----------|----------------|
| US-AUTH-01 | As a user, I can sign in with Google OAuth so that only authorized people access the system. | P0 | Phase 1 |
| US-AUTH-02 | As an admin, I can assign roles (user, content_admin, operator) so that privileges are least-privilege. | P0 | Phase 1–2 |
| US-AUTH-03 | As a security officer, I can see audit logs of admin actions without PII in free-text fields. | P1 | Phase 2 |

### 3.2 Document Management & Versioning

| ID | Story | Priority | Phase (target) |
|----|-------|----------|----------------|
| US-DOC-01 | As a content admin, I can upload PDF/DOCX/Markdown/HTML documents. | P0 | Phase 2 |
| US-DOC-02 | As a content admin, I can publish a new **version** of a document without deleting history. | P0 | Phase 2 |
| US-DOC-03 | As a content admin, I can retire or unpublish a version so it is no longer retrieved. | P0 | Phase 2 |
| US-DOC-04 | As a user, when I receive an answer, I can see **which document version** was used. | P0 | Phase 3 |
| US-DOC-05 | As an operator, I can re-index a document version after pipeline fixes. | P1 | Phase 2–3 |

### 3.3 Question Answering (RAG)

| ID | Story | Priority | Phase (target) |
|----|-------|----------|----------------|
| US-QA-01 | As a user, I can ask a natural-language question and receive a grounded answer. | P0 | Phase 3 |
| US-QA-02 | As a user, I see **citations** (document title, section/chunk, version) with each answer. | P0 | Phase 3 |
| US-QA-03 | As a user, when the system lacks evidence, I get a clear “insufficient evidence” response rather than a guess. | P0 | Phase 3 |
| US-QA-04 | As a user, I can follow up in a multi-turn conversation with context retained for the session. | P1 | Phase 4 |
| US-QA-05 | As a user, I can filter questions to a document set/collection. | P1 | Phase 4 |

### 3.4 Voice

| ID | Story | Priority | Phase (target) |
|----|-------|----------|----------------|
| US-VOICE-01 | As a user, I can speak a question (STT) and receive a spoken answer (TTS) in the PWA. | P1 | Phase 5 |
| US-VOICE-02 | As a user, I can cancel voice capture and fall back to text. | P1 | Phase 5 |
| US-VOICE-03 | As an operator, I can configure STT/TTS providers without code changes (config/Secret Manager). | P2 | Phase 5 |

### 3.5 Guardrails & Safety

| ID | Story | Priority | Phase (target) |
|----|-------|----------|----------------|
| US-GRD-01 | As a security officer, I require prompt-injection and jailbreak attempts to be blocked or neutralized. | P0 | Phase 3–4 |
| US-GRD-02 | As a security officer, I require PII redaction in logs and analytics (hash user IDs). | P0 | Phase 1+ |
| US-GRD-03 | As a user, I never receive answers that cite documents I am not authorized to access. | P0 | Phase 3 |
| US-GRD-04 | As an operator, I can tune refusal thresholds and safety policies via config. | P1 | Phase 4 |

### 3.6 Analytics & Observability

| ID | Story | Priority | Phase (target) |
|----|-------|----------|----------------|
| US-ANL-01 | As a product owner, I can view query volume, latency percentiles, and refusal rates. | P1 | Phase 6 |
| US-ANL-02 | As an operator, I can view p50/p95/p99 latency and error rates on a dashboard. | P0 | Phase 1+ (basic), Phase 6 (full) |
| US-ANL-03 | As a product owner, I can track answer quality metrics on a held-out evaluation set. | P1 | Phase 6 |
| US-ANL-04 | As a security officer, I confirm analytics tables do not store raw query text or PII. | P0 | Phase 6 |

### 3.7 PWA & UX

| ID | Story | Priority | Phase (target) |
|----|-------|----------|----------------|
| US-PWA-01 | As a user, I can install the app as a PWA on mobile/desktop. | P1 | Phase 5 |
| US-PWA-02 | As a user, I get a usable offline shell (cached UI) when the network is unavailable. | P2 | Phase 5 |
| US-PWA-03 | As a user, I can copy answers and open citation sources. | P0 | Phase 3 |

### 3.8 Platform & Ops

| ID | Story | Priority | Phase (target) |
|----|-------|----------|----------------|
| US-OPS-01 | As an operator, I can deploy API and UI to Cloud Run via automated pipelines. | P0 | Phase 1–2 |
| US-OPS-02 | As an operator, all infrastructure is defined in Terraform and is idempotent. | P0 | Phase 0–1 |
| US-OPS-03 | As an operator, secrets never appear in git or container env files committed to the repo. | P0 | Phase 0+ |

---

## 4. Non-Functional Requirements (NFRs)

### 4.1 Performance
| ID | Requirement | Target (initial) |
|----|-------------|------------------|
| NFR-PERF-01 | Interactive text Q&A latency | p50 < 3s, p95 < 8s (dev; tighten after baseline measure) |
| NFR-PERF-02 | Ingestion throughput | Document-dependent; async job; no blocking of query path |
| NFR-PERF-03 | Cold start (Cloud Run) | Acceptable in dev; min-instances strategy for prod later |

> **Note:** Latency gates must be set from measured baselines (actual − 2% buffer), not aspirational numbers.

### 4.2 Reliability
| ID | Requirement |
|----|-------------|
| NFR-REL-01 | Stateless API instances; horizontal scale on Cloud Run |
| NFR-REL-02 | Idempotent ingest and publish operations |
| NFR-REL-03 | Health and readiness endpoints for deploy smoke tests |

### 4.3 Security
| ID | Requirement |
|----|-------------|
| NFR-SEC-01 | Least-privilege service accounts; roles listed in runbooks |
| NFR-SEC-02 | Secrets in Secret Manager only |
| NFR-SEC-03 | CMEK on GCS (and other supported data stores) from foundation phase |
| NFR-SEC-04 | Non-root container user (uid/gid 1001) |
| NFR-SEC-05 | No PII in application logs; hash user identifiers |
| NFR-SEC-06 | detect-secrets (or equivalent) in CI when CI is introduced |

### 4.4 Privacy & Compliance
| ID | Requirement |
|----|-------------|
| NFR-PRV-01 | Analytics: hashed user IDs + metadata only (no raw query storage by default) |
| NFR-PRV-02 | Document access enforced at retrieval time (ACL / collection scope) |
| NFR-PRV-03 | Design for DPDP Act 2023 considerations (India); document data residency in ADRs |

### 4.5 Observability
| ID | Requirement |
|----|-------------|
| NFR-OBS-01 | Structured JSON logging (Cloud Logging compatible) |
| NFR-OBS-02 | Trace query path: retrieve → generate → respond with correlation IDs |
| NFR-OBS-03 | Metrics: latency percentiles, error rate, token usage, retrieval hit rate |
| NFR-OBS-04 | Alerting for critical thresholds (wired in ops phase) |

### 4.6 Maintainability
| ID | Requirement |
|----|-------------|
| NFR-MNT-01 | ADRs for every significant architecture decision |
| NFR-MNT-02 | `docs/backlog.md` living backlog; `CHANGELOG.md` per release/PR set |
| NFR-MNT-03 | Pinned dependencies; CI installs only from declared files |
| NFR-MNT-04 | Three-Agent Protocol followed for design/build/verify |

### 4.7 Cost
| ID | Requirement |
|----|-------------|
| NFR-COST-01 | Scale-to-zero friendly in non-prod |
| NFR-COST-02 | Visibility of LLM/embedding token cost in analytics phase |
| NFR-COST-03 | No unbounded re-embed loops without rate/budget controls |

---

## 5. Out of Scope (Phase 0–1)

- Multi-region active-active
- Native iOS/Android apps (PWA first)
- Full multi-tenant SaaS billing
- On-prem deployment
- Fine-tuning custom LLMs (prompt + RAG first)

---

## 6. Success Criteria (Platform MVP)

1. Authenticated user can upload a document, publish a version, and ask a question with citations.
2. Guardrails refuse ungrounded answers under empty retrieval.
3. Analytics path stores no raw PII.
4. Infra for core services is Terraform-managed and redeployable.
5. Evaluation set exists and is used for quality gates (not training-time contamination).

---

## 7. Traceability

| Artifact | Path |
|----------|------|
| Architecture ADR | `docs/adr/0001-high-level-architecture.md` |
| Tech stack ADR | `docs/adr/0002-tech-stack.md` |
| Living backlog | `docs/backlog.md` |
| Engineering protocol | `docs/grok-three-agent-protocol.md` |
