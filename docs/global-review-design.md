# Global PR review gate — design guide

[日本語：canonical engineering specification](global-review-design.ja.md) · [Home](../README.md)

**Documentation only; implementation planned from 2026-11-18 JST. Nothing is activated.** The Japanese specification is normative; this companion provides navigation.

## Current truth

Baseline: `main` at `3be4c4739b046ad7e52642d98aff11c6fc8d664f`, including PR56 repair `1695df06`. Extend existing polling, reservations and signed one-target authorization. Checked-in recurring gates are false; current runtime variables, installation permissions, account/plan and protections are UNKNOWN. Historical real reviews were incomplete; old-base runs do not accept the correction. Reconcile conflicting mock records in P0; do not combine or replay them.

Alibaba OpenCodeReview v1.13.7 and Cloudflare guidance (`c1c8a8c1471069fb0e188eeaff69b8e8db6564a8`) both use Xiaomi MiMo `mimo-v2.6-pro`: different methods are not provider independence. Lane success is not aggregate acceptance.

## Specification map

| Japanese section | Contract |
|---|---|
| 1–2 | Invariants; source/live/history/UNKNOWN reconciliation |
| 3 | Architecture diagram; proposed signed/deduplicated webhook, existing poll fallback, pinned controller/adapters, isolated CI |
| 4 | Existing/future public/private repositories; drafts, forks, branches, backlog, large/unsupported inputs, transfers, App removal, hub and upstream boundaries |
| 5 | Canonical identity; event/job/finding/lane/aggregate schemas; dedupe, leases, reservations, stale invalidation and CI binding |
| 6 | Plan-dependent org rulesets or personal bootstrap; expected App, enrollment, protection race, drift and audited exceptions |
| 7 | Validated finding → bounded separate worker → independent review → fresh CI/review; human merge, proposed two-cycle cap |
| 8 | P0 truth → P1 one-repo no-write gate → P2 coverage/enrollment → P3 human-approved repair; files, dependencies, DoD, rollout/abort and T01–T14 |
| 9–10 | Privacy/retention, metrics, runbook, kill-switch, handoff and open decisions |

## Gate contract

Proposed required Check: `global-review/merge-gate`, separate from existing lanes. `success` requires full valid coverage, required provider independence, no blocking findings, trusted required CI explicitly successful, and fresh matching identity. Pending/running have no conclusion; findings/manual/incomplete/oversized use `action_required`; error/unknown/stale use `failure`; abort uses `cancelled`. Never pass `neutral`/`skipped`. Bind CI to expected App/workflow source, not merely its name. Section 5 specifies test-merge parents and separate merge-group identity; invalidate old evidence/approvals on identity changes.

No partial green or secret-bearing privileged PR execution. Private export needs consent; forks, non-default branches, queues and unsupported inputs need separate acceptance. App installation alone provides no merge protection; disclose effective administrator bypass and foreign-upstream limits. Read-only reviewers cannot push. Separate workers have bounded authority; this design grants none. Planned worker: Claude Code CLI `claude-sonnet-5-5`, no silent fallback.

## Acceptance and operations

T01–T14 are **proposed; execution count zero here**. Preserve historical records, budgets and UNKNOWN reservations: timeout/lease expiry grants no retry or refund. Kill-switch stops dispatch without greening pending/error gates; retain protections and human merge hold. P1 must prove actual merge blocking before expansion; P3 starts with human-approved handoff, not automatic writes.

The existing collector limits both diff and combined before/after snapshots to 65,536 bytes (20 paths). Keep documentation changes within both budgets without omitting required design or historical evidence; oversize input is not a review finding or model failure.

See sections 9–10 for retention, live plan/protection gaps, private consent, independent provider, quotas, webhook/ledger, unsupported coverage and explicit repair budgets.
