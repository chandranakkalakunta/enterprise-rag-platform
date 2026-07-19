# Phase 5 Retrospective — Full PWA / UI

**Date:** 2026-07-19  
**Status:** Complete  
**PR range:** #24 – #28 (approx.; ADRs 0009/0010 through 5.4 PWA install)

## Summary

Phase 5 delivered the **production-facing PWA**: Google auth + roles, chat with grounded answers/citations, admin upload/publish/retire, installable shell with offline shell-only, and mandatory backend version auto-reload.

**Native app stores remain out of scope.**

## Delivered

| Sub-phase | What |
|-----------|------|
| **5.0** | ADR-0009 AuthN/AuthZ + Firestore roles; ADR-0010 PWA + health version reload |
| **5.1** | Google ID token verify; domain allowlist; `GET /me`; Next.js shell; VersionWatcher |
| **5.2** | Chat UI → `POST /api/v1/query/answer`; refusal + citations |
| **5.3** | Admin upload/list/publish/retire; GET documents; chat ↑ history + `/clear` |
| **5.4** | Manifest + SW installability; citation title fallback; upload title=filename; gen model default `gemini-2.5-flash` |

## Lessons

1. **Backend is source of truth for roles** — UI gates alone are insufficient; 403 on mutations saved us from fake client flags.  
2. **Health `version`/`deployed_at` reload** is a simple, effective fix for long-lived PWA/tabs after Cloud Run deploys.  
3. **Offline honesty** (shell only) beats fake offline RAG.  
4. **Default model pins rot** — keep `GENERATION_MODEL_ID` env-overridable; retired Gemini 2.0 id broke live gen until updated.  
5. **Document title defaults matter** for citation UX (`Untitled` vs filename).

## Deferred (not incomplete Phase 5 MVP)

| Theme | Item |
|-------|------|
| Voice | STT/TTS in-PWA (BL-VOICE-*) |
| Multi-turn | Server-side conversation history (Phase 4) |
| Feedback stars | US-QA-06 / BL-FB-* |
| Full offline | N/A by design for answers |
| LB + Armor | Phase 6+ |
| Streaming answers | Backlog |

## Residual risks

- ID token in sessionStorage (XSS surface); BFF/httpOnly later.  
- Gmail allowlist breadth if URL is public.  
- SW shell cache vs. Next.js hashed `/_next/static` assets (network/cache hybrid; full Workbox optional later).  
- Sync upload/embed/generate still on API path (latency).  

## Next (Coordinator order)

1. **Phase 4** — RAG quality (hybrid BM25+RRF, multi-turn, ACL depth, fuller guardrails).  
2. **Phase 6** — analytics / eval / Binary Auth / HTTPS LB + Cloud Armor.  

Delivery order after Phase 3 remains **5 (done) → 4 → 6**.
