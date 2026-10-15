# Final Limited Escalation to Claude Opus 5.5 Medium — Operating Decision 2026-10-15

[English](operating-decisions-2026-10-15.md) | [日本語](operating-decisions-2026-10-15.ja.md)

Recorded: 2026-10-15 (Asia/Tokyo). This extends the [2026-10-13 operating update](operating-decisions-2026-10-13.md) and the [2026-10-10 allocation policy](operating-decisions-2026-10-10.md). Earlier dated records and observations are retained unchanged. Model names are owner-reported operating labels, not API IDs or proof of runtime identity.

## Decision (owner operating judgment)

When a hard problem stalls under the owner-selected GPT/Sol worker (usually GPT-6.1 Sol / Medium for difficult work), the owner may make **one final, limited escalation to Claude Opus 5.5 Medium**. This is the owner's operating judgment from experience. It is **not** a claim that Opus is objectively best or always better than Sol, and no benchmark or comparison is asserted.

Roles are otherwise unchanged: routine implementation remains Claude or Antigravity Sonnet; Codex designs, coordinates and reviews; Dottie remains PM; the owner accepts.

## Trigger

Consider escalation only when, under the owner-selected GPT/Sol worker, either:

- the same failure repeats, or
- there is no concrete progress within the agreed work limit.

## Before escalating

1. **Preserve** the phenomenon, reproduction steps, attempted methods and their results, unverified items, constraints, acceptance criteria, and the smallest non-secret source/revision needed to reproduce.
2. **Check token capacity and cost** before bounded delegation. Missing or stale observations are `unknown`; do not route as if they were current, and do not add unlike provider token units.
3. **Record** requested model/effort separately from observed runtime model/effort (`UNKNOWN` unless evidenced).
4. Confirm the route is authorized: respect permissions, TLS certificate validation, secrets handling and paid-action approvals.

## During and after

- Never bypass a denial and never silently change the runtime, model, TLS settings or permissions. On denial, preserve the work and stop for the correct approval path.
- Keep the delegation bounded by the stated work limit; one escalation, not an open-ended loop.
- Review the **current** revision and its evidence (stale-head or builder-only review is not independent review).
- After completion or the work limit, **return to the ordinary model** for the task.

## Evidence status

| Item | Status |
|---|---|
| RunPod Phase 2 connection test passed with Claude Opus 5.5 Medium | **Owner report (本人報告).** No independent test log, Pod termination or billing-stop confirmation has been checked by the maintainers. |
| Independent A100 review quality | **Not accepted.** A connection pass is not review-quality evidence. |
| Automated operation (startup, connection, review, termination) | **Not accepted.** |
| Mattermost | A difficult-problem **example only**; not stated as completed. |

The earlier statements "Phase 2 is mock/offline only" and "Codex is always the final escalation" are dated snapshots (2026-10-13 and before). For Phase 2, an owner-reported connection pass now exists, kept separate from the unaccepted review-quality and operation status above; for escalation, this decision adds the limited Opus step described here. Neither changes Qwen review acceptance.

## Non-changes

Documentation only. No GPU was started and no model configuration, TLS setting, permission or runtime setting was changed. No costs or verification are claimed beyond the owner report above.

See the [routing guide](routing-guide.md), [roles](ai-team.md), [handoff template](handoff-templates.md) and [changelog](../CHANGELOG.md).
