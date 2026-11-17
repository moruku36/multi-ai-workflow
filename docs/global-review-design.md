# Global PR review gate — design guide

[日本語：canonical engineering specification](global-review-design.ja.md) · [Home](../README.md)

**Documentation only. Implementation is planned from 2026-11-18 JST. Nothing is activated by this change.** The Japanese specification is the normative, owner-readable detailed design; this English companion is its navigation and contract summary, not a separate implementation specification.

## Current truth

Source baseline: `main` at `3be4c4739b046ad7e52642d98aff11c6fc8d664f`. This includes PR56's `1695df06` repair. Existing central polling, reservations and signed one-target authorization are extended, not replaced. Checked-in recurring gates are false. Current runtime variables, installation permissions, account/plan and protections are unknown. Historical real reviews were incomplete; old trusted-base runs do not accept the new correction. Historical mocked-case records disagree across evidence sources and must be reconciled in P0, not added together or replayed.

Alibaba OpenCodeReview v1.13.7 and Cloudflare guidance pinned at `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8` currently execute through Xiaomi MiMo `mimo-v2.6-pro`. Different methods on one provider are not provider independence. Existing lane success is not aggregate CI/independence/human acceptance.

## Specification map

| Japanese section | Engineering contract |
|---|---|
| 1–2: purpose and reconciliation | Source pointers, implemented vs historical/live vs unknown, acceptance gaps |
| 3: architecture | Proposed signed/deduplicated App webhook ingress plus existing polling fallback; trusted pinned controller and reusable adapters; isolated CI |
| 4: coverage | Public/private/future repositories, drafts, forks, non-default targets, old backlog, large changes, deletions/renames/binary/submodules/generated files, archive/transfer/App removal and hub self-review |
| 5: contracts | Installation/repository ID, PR/head/base/merge-base, policy/controller/engine/source digests; event/job/finding/lane/aggregate receipts; idempotency, leases and stale invalidation |
| 6: enforcement | Org rulesets only where plan/account permits; personal per-repo bootstrap; expected App binding, future-repo race, drift audit and scoped audited human exceptions |
| 7: repair loop | Validated findings → data-separated instructions → separate write worker → isolated patch → independent review → new-head CI/review → human merge; proposed max two cycles |
| 8: implementation | P0 truth, P1 one-repo no-write gate, P2 coverage/protection/webhook, P3 human-approved fix handoff before bounded automation; proposed files, dependencies, DoD, rollout and abort |
| 9–10: operations | Privacy-safe receipts, retention proposal, metrics, onboarding, safe kill-switch, runbook and unresolved decisions |

## Non-negotiable gate semantics

The proposed required Check is `global-review/merge-gate`, distinct from existing lane Checks. Only complete valid reviews, required provider independence, resolved blocking findings, current trusted CI and a fresh matching identity can produce `success`. Pending/running have no conclusion; unresolved findings/manual/incomplete/oversized become `action_required`; error/unknown/stale become `failure`; deliberate abort is `cancelled`. Never emit `neutral` or `skipped` as a passing required gate. Bind required checks to the expected App/source; same-name checks from other integrations or PR-edited policy are not evidence.

No partial coverage is green. Private source export consent is unresolved: off/manual by default. Forks, non-default branches, merge queue and unsupported blobs require separate acceptance. All-repositories App access does not install merge protections, and administrators with effective bypass can defeat enforcement; disclose that limitation. Foreign upstream enforcement is outside owner control.

Latest-head checks alone are insufficient when base, policy or reviewer version moves. Invalidate the old identity, including approvals; merge queue needs a separate merge-group SHA contract. Unknown or timed-out reservations remain consumed until reconciled; no blind retries or refunds. The read-only reviewer App cannot push; a separate limited worker authority would be needed, and this document grants none. The next selected implementation worker is planned as Claude Code CLI `claude-sonnet-5-5`, with no silent fallback or provider-independence assumption.

## Rollout and verification

P0 reconciles source/live truth and old UNKNOWNs. P1 proves one repository can block merge on missing/failed review or CI without any repair write. P2 adds explicit enrollment and protection/drift coverage before claiming all existing/new repositories. P3 first hands validated findings to humans; low-risk bounded automation needs a later decision.

All T01–T14 acceptance scenarios in the canonical specification are **proposed, execution count zero for this documentation task**: known-good, actual-bug/counterexample, outage/incomplete, stale/base/policy, replay/concurrency, unprotected new repo, fork attacks, input boundaries, private/draft/backlog, forged CI source, App removal/transfer/truncation, queue identity, correction limit/UNKNOWN and out-of-scope writes. Old budgets and reservations are not reset. Kill-switch stops dispatch, never converts pending gates to green; preserve protections and human merge hold.

Open decisions include live account/plan features, private model consent, independent provider, hard quotas, webhook hosting/durable ledger, fork/queue/large-input support and explicit repair time/token/cost budgets. See the canonical specification for the full source matrix, JSON sample, file-level work units, retention proposal and operator handoff.
