# ADR-0004: Guardrails Architecture

## Status

Accepted — 2026-07-16

## Context

Enterprise RAG systems face: prompt injection via documents or users, jailbreak attempts, unauthorized data leakage through retrieval, ungrounded hallucinations, and privacy leakage via logs/analytics.

We need a **layered** guardrail design that is enforceable in code, observable via metrics, and tunable later via config (US-GRD-04) without weakening defaults.

## Decision

### Defense-in-depth layers

| Layer | When | Controls |
|-------|------|----------|
| **L0 AuthZ** | Every request | RBAC + authenticated principal |
| **L1 Input** | Pre-retrieval | Size limits, rate limits, basic injection heuristics, strip control tokens where applicable |
| **L2 Retrieval ACL** | Pre-fusion | Filter chunks by document/collection ACL **before** ranking fusion |
| **L3 Grounding gate** | Pre-generation | If no/low-evidence chunks → **refuse** (no generative guess) |
| **L4 Prompt hygiene** | Generation | Separate system policy from untrusted user text and untrusted document text; documents marked as data |
| **L5 Output** | Post-generation | Ensure citations present when claims require them; block responses that cite out-of-ACL ids (defense-in-depth); optional sensitive pattern scrub for logs |
| **L6 Privacy egress** | Logging/analytics | Hashed subject ids; metadata-only analytics; no raw query default |

### Refusal policy (MVP)

Refuse (structured `refusal_code`) when:

1. Retrieval returns zero usable chunks for the principal’s ACL.  
2. Top evidence score/confidence below configured threshold (threshold defaults conservative).  
3. Input classified as clear jailbreak/injection attempting policy bypass **and** safe answer is not possible from corpus (prefer refuse over clever compliance).  

User-visible copy is calm and actionable (“I couldn’t find this in your authorized documents”), not model-internals.

### Untrusted content rule

- User messages and document chunks are **never** treated as system instructions.  
- Tool/admin instructions live only in trusted system prompts and server-side config.

### Observability

Emit counters (not raw attack payloads by default):

- `guardrail.input_block`  
- `guardrail.refusal` (by code)  
- `guardrail.output_block`  

Correlate with `correlation_id`.

### Configuration

- Defaults shipped in code (safe).  
- Operator overrides via config/Secret Manager in Phase 4 (US-GRD-04).  
- Invalid config → fail closed to defaults.

## Rationale

- Layering matches real attack paths (input, retrieval leak, generation, egress).  
- Grounding gate is the primary anti-hallucination control for enterprise Q&A.  
- ACL at retrieval is mandatory; output filter is backup only.  
- Privacy egress aligns with NFR-PRV-01 and prior production HR RAG practice.

## Consequences

### Positive
- Clear implementation map for services/guardrails  
- Testable contracts (unit + integration ACL tests)  
- Metrics for product and security  

### Negative
- Over-refusal risk if thresholds too tight (tune with held-out eval, not production guessing)  
- Slight latency overhead for checks (should be small vs LLM)

### Risks and Mitigations
- **Risk:** Injection buried in PDFs  
  - **Mitigation:** L4 prompt hygiene + treat docs as data; optional content scanners later  
- **Risk:** Citation fabrication  
  - **Mitigation:** Only attach citations from retrieved chunk ids; validate ids server-side  

## Alternatives Rejected

### Single “moderation API only” without grounding gate
- Why rejected: Does not ensure corpus grounding

### Client-side only filtering
- Why rejected: Trivially bypassable

### Store full prompts/attacks in analytics by default
- Why rejected: Privacy and retention risk

## References

- [ADR-0001](./0001-high-level-architecture.md)  
- [architecture/overview.md](../architecture/overview.md)  
- [requirements.md](../requirements.md) (US-GRD-*, NFR-SEC/PRV)  
- [ui-specs.md](../ui-specs.md) (refusal presentation)  
