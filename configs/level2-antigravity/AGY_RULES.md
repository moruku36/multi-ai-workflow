# Antigravity / Gemini Task Guidance

[English](AGY_RULES.md) | [日本語](AGY_RULES.ja.md)

This file describes task guidance, not a fixed global model or effort default. Model labels are owner-reported; request labels do not prove the runtime model or CLI identifier.

## Choose per task

- Use Gemini/Antigravity when its capabilities and environment suit the task, such as a PoC, mock, exploration, or bounded implementation.
- Select the requested model and effort for the task's difficulty, quality bar, environment, fresh capacity evidence, and cost. Respect an explicit user choice for that task without making it a universal default.
- Antigravity's Gemini pool and Antigravity Claude/GPT pool are separate. Both differ from native Gemini/Claude/Codex subscription pools. API charges are not subscription quota.
- Direct Claude Code uses a separate capacity pool from Claude inside Antigravity.
- A Gemini-first then Claude refinement route is optional, not a fixed sequence. Keep or improve an existing implementation instead of requesting duplicate initial implementations.

## Boundaries

- Report requested model/effort separately from observed runtime. Use `unknown` unless evidence proves runtime identity.
- CodexBar quota images are manually checked. Automated quota retrieval/routing is not verified; stale or missing observations are `unknown`.
- A web remote-control request accepted or shown as Working does not prove implementation, tests, or automated integration. Local CLI access is a separate route and may remain unavailable.
- Separate user approval, execution-environment authorization, local tests, and live deployment. If proper approval is denied, preserve the work and stop; do not bypass through retries or a different route.
- Make bounded changes, run relevant checks when authorized, and report changes, tests, blockers, and unresolved runtime status.

See the [routing guide](../../docs/routing-guide.md), [operating decisions](../../docs/operating-decisions-2026-10-05.md), and [handoff templates](../../docs/handoff-templates.md).
