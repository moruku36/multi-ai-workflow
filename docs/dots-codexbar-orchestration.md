# Dottie, CodexBar, and Handoff Boundaries

> Status snapshot: 2026-10-05. Manual quota review is in use; live quota ingestion and fully automatic dispatch are unverified.

This document separates PM coordination from capacity tooling and reusable engineering handoffs. Dottie is the PM. Factory provides a minimal handoff/artifact/evidence layer. AIteamBridge is a separate local capacity/router/transport implementation project. They are complementary components, not competing claims of a complete autonomous orchestrator.

## Runtime topology

- Windows is the always-on local base.
- Mac is a secondary helper environment.
- Dottie owns task scope, provider/environment selection, progress, acceptance, and review coordination.
- One selected engineer performs the bounded task; Factory can preserve handoff and evidence for reuse.

```mermaid
flowchart TD
    U["Product Owner"] --> D["Dottie<br/>PM / task / acceptance"]
    D --> A["Selected tool and environment"]
    A --> F["Factory<br/>thin handoff + artifact + evidence"]
    F --> D
    B["AIteamBridge<br/>local capacity / router / transport project"] -. "live retrieval and autonomous dispatch unverified" .-> D
```

## Capacity observation

- CodexBar images are manually inspected. Do not describe automated screenshot reading or a live automatic quota feed as operational.
- Preserve quota window, provider pool, observation timestamp, and freshness in any future normalized record.
- Session and weekly windows are distinct. Five hours without activity does not mean a 100% reset.
- Direct Claude Code, Antigravity Claude/GPT, Antigravity Gemini, and native Codex have distinct pools. API charges are separate from subscription quota.
- Missing, stale, or ambiguous evidence is `unknown`; return to a manual choice.
- Routing depends on task difficulty, quality, environment, fresh capacity evidence, consumption pace/reset, and cost, rather than fixed quota thresholds.

## Current verification boundary

- Factory's minimal handoff is verified in [PR #29](https://github.com/moruku36/ai-engineering-factory/pull/29), merged at `4fb014a`, including Ubuntu/Windows quality gates and offline container-boundary verification.
- Bridge capacity/router work is reported at 246 local/offline tests, uncommitted and unpublished. Live quota retrieval and autonomous dispatch are unverified; recheck that repository before treating the count or state as current.
- A user-provided Antigravity Web Remote Control session showed the desktop connection and Gemini 3.8 Flash High selection. A read-only request about DateMemory was sent and displayed as Working. This verifies request acceptance through that web route only; it does not prove implementation, tests, completion, or automatic integration. Do not include connection URLs, instance IDs, hostnames, or other private connection details.
- Local Windows CLI received an access-denied response and remains unverified. The web route and local CLI are different routes.
- User approval, execution-environment authorization, local test results, and live environment reflection are separate stages. Preserve work and stop when the proper approval is denied; do not retry in a loop or bypass it via another route.

## Privacy and future work

Never pass provider credentials, cookies, or account content into a router. Do not publish exact balances, cost values, quota screenshots, private conversations, connection identifiers, or logs. Future quota/router work should fail closed on stale/unknown observations and log only sanitized evidence. No automatic execution should be claimed before its exact provider route, authorization, result readback, and acceptance checks are verified.
