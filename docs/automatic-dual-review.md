# Automatic Alibaba + Cloudflare-guided PR review

[日本語](automatic-dual-review.ja.md)

## Current state — 2026-11-12

The implementation is on main and repository PR review is activated. A
[bounded smoke run](https://github.com/moruku36/multi-ai-workflow/actions/runs/43008525402)
succeeded, but the later reviews for [#49](https://github.com/moruku36/multi-ai-workflow/pull/49)
and [#50](https://github.com/moruku36/multi-ai-workflow/pull/50) recorded
`INCOMPLETE`, with both lanes `FAILED_OR_UNKNOWN`. Merging those PRs did not
turn failed reviews into successful evidence or activate the
[central review hub](central-review-hub.md), whose two config gates remain false.

## What runs

When activated, every PR opened, updated, reopened or marked ready against main
triggers two source-only lanes:

1. Pinned Alibaba OpenCodeReview v1.13.7, using MiMo mimo-v2.6-pro through the
   existing bounded relay, with only task_done/code_comment tools enabled.
2. A separate MiMo source-only reviewer supplied the pinned Cloudflare
   security-audit SKILL, ATTACK-CLASSES and VALIDATION-AND-REPORTING companions.
   This executes the OSS guidance, not the full six-phase audit. No tools,
   independent verifier, target execution or full-coverage claim.

Both receive the actual merge-base/head change, not synthetic fixture results.
Both use Xiaomi/MiMo; they are two methodologies, NOT independent providers.
The receipt binds original diff hash and immutable revisions. Alibaba inspects a
disposable before/after source snapshot of the changed regular text blobs;
commit metadata and unchanged repository context are outside its coverage.
Deletion-only, executable-mode, binary, symlink, submodule, oversized or unsupported
changes can be blocked rather than silently accepted. Limits are 20 paths,
64 KiB original diff and 64 KiB cumulative before/after source.

## Setup and revalidation

For a new installation, follow these steps; this repository has already merged
and activated its PR workflow, but broad live acceptance remains outstanding.

1. Review and merge the implementation. The workflow uses the trusted base
   version; it cannot validate itself on its installation PR.
2. Set the existing MiMo key as the repository Actions secret MIMO_API_KEY using
   GitHub Settings → Secrets and variables → Actions. Do not commit it.
3. Set repository variable DUAL_REVIEW_ENABLED to true after accepting the
   recurring-call limits below. No authentication or variable settings are
   changed by these instructions.
4. Open/update a small PR and inspect both lane receipts and the check on its
   exact head. A single successful smoke run does not establish general
   coverage or recovery from later failures.

Missing activation or secret fails visibly. Fork contributions are source data;
no fork script/workflow is executed with secrets. PRs to other base branches and
local uncommitted edits are not covered. No schedules, push trigger or auto-merge.

## Resource and retry limits

Per eligible event: Alibaba at most 8 HTTP attempts (including failures), 64 KiB
request body, 2,048 output tokens/request; Cloudflare at most 1 HTTP attempt,
192 KiB request body, 2,048 output tokens. Provider timeout 30s, Alibaba process
150s, entire job 8min. The controller has no upstream retries or redirect following.
There is NO enforced dollar cap and no cumulative daily spending cap. Repository
activation explicitly enables recurring paid calls; use provider billing limits
for a monetary ceiling. Stop activation by setting DUAL_REVIEW_ENABLED=false.

A durable check-run reservation precedes any model call. The repository-wide
concurrency group serializes reservations. Same base-tip/head is never
automatically replayed, even after partial failure or workflow rerun. A lost
reservation response, interruption or unknown model result requires manual
reconciliation; do not erase the marker or blindly rerun. New head/base pairs
are new billable reviews. GitHub may coalesce pending concurrency jobs during
rapid updates; only the latest surviving head is guaranteed to be scheduled,
not every transient commit. Base-only branch movement does not itself trigger
a run; update the PR to obtain a fresh binding.

## Results and trust

The dual-review-receipt check is failure for partial/stale results, action_required
for findings or validation gaps, and success only for two completed source-only
reviews with no recorded findings/gaps. Success is NOT quality acceptance,
independence verification, finding adjudication or merge authority.
The workflow itself also fails when execution is incomplete.
An always-attempted, seven-day Actions artifact holds the JSON receipt; no raw
model text is printed to CI logs or posted as comments. Artifacts inherit repo
Actions visibility: findings are repository-visible, not private host reports.
No private local reports are uploaded. No branch-protection policy is changed.

The controller, skill and dependencies come from the trusted main base SHA;
PR blobs are fetched and read with Git object APIs only. No PR checkout,
hooks, custom tools, dependencies, tests or builds run. Provider keys stay in
the parent process; the CLI receives only a one-run loopback bearer token and
a small environment allowlist. Model-directed filesystem/search tools are
disabled. Provider errors and arbitrary model content are not echoed.

## Verification state

Four earlier selected offline cases passed: real-diff extraction,
unsupported-input rejection, the pinned CLI loopback path and duplicate/unknown
reservation refusal. The central coordinator separately has five passing mocked
offline cases. These are not evidence of live provider quality or cross-repository
durability, and were not rerun for this documentation update.

The smoke run above succeeded at head
`5606fbdc13025ed6b816470f6c64d0419f7ce7e4`. Later
[core](https://github.com/moruku36/multi-ai-workflow/actions/runs/43075852872)
and [workflow/docs](https://github.com/moruku36/multi-ai-workflow/actions/runs/43075924119)
runs failed at their own immutable heads. Their failed-lane receipts do not
establish the precise failure cause, actual HTTP count or bill. Do not infer
zero cost or retry the reserved pairs. The existing Alibaba adapter's unsupported
Markdown handling is still unresolved on main.

Next: preserve failed receipts, diagnose the actual lane failures, review and
verify the repair, and perform bounded current-revision acceptance. Keep central
recurring execution disabled until its separate policy and live acceptance gates
are satisfied.
