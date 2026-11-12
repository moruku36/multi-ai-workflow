# Central review hub

[日本語](central-review-hub.ja.md)

**Inactive draft; local evidence only.** The earlier five mocked offline test
cases were reported passed in one invocation and have not been rerun. The later
three mocked repair cases are reported as **3 PASS / 1 invocation / 0.005s**;
they were not rerun for this readiness change and are not live acceptance.
The workflow and live integration have not been accepted on a real PR. Both `enabled` and
`paid_execution_authorized` in [the central config](../config/central-review-hub.json)
are currently `false`. These files do not establish live automation or review
quality acceptance.

## One-time central setup

1. Create a GitHub App with repository permissions **Contents: read**, **Pull
   requests: read**, and **Checks: read and write**; GitHub also supplies mandatory
   Metadata read access. No Actions, administration, or source write permission is
   needed. Install it on the configured owner with **All repositories**, including
   the hub. This covers current and future repositories under that installation.
   The token can access private installation repositories even though discovery
   excludes them; protect the hub and App key accordingly.
2. In the hub alone, configure Actions variable `APP_ID` and secret
   `APP_PRIVATE_KEY`. Keep the existing `MIMO_API_KEY` secret in the hub alone.
   No target workflow, key, setting, or code-policy change is required per target.
   The pinned App-token action receives the owner and deliberately omits
   `repositories`, giving discovery access to the whole installation. It explicitly
   requests Contents read, Pull requests read, and Checks write. `GITHUB_TOKEN`
   has only Contents read; the App token supplies cross-repository writes.
3. Complete one central code-policy review of the trusted workflow, controller,
   config, all-repository access, provider source disclosure, reservation limits,
   and recurring paid execution. Resolve findings and the repository's required
   review/acceptance gates. In that reviewed central change, explicitly authorize
   paid execution and set **both** `enabled: true` and
   `paid_execution_authorized: true`. Merge through the existing human gates onto
   trusted `main`. This is a future activation procedure, not authorization from
   the draft itself.
4. After the human merge, obtain a **new explicit paid allowance** for one bounded,
   fresh real-target PR acceptance on the reviewed trusted revision. Reconcile
   consumed reservations first; use a fresh, unreserved immutable base/head/diff
   binding within the unchanged 20-path and 65,536-byte diff and total
   before-plus-after blob caps. Oversized input stays blocked: do not increase
   caps or omit paths. Complete both actual-source lanes, record the actual
   provider/model, resolve findings, and meet independence and human acceptance
   gates. Keep recurring execution disabled. A separately reviewed bounded
   acceptance route while that gate is off has not been established here; until
   available, this step is blocked. Caller flags and local evidence cannot bypass
   that missing route or authorize spend.
5. Read back the final target Check/receipt and hub reservation/ledger. Confirm
   the exact current base/head/diff, completion and safe diagnostics, retained
   consumed failures/unknowns, and durable deduplication across hub revisions.
   Accept those readbacks explicitly; mocks or a successful Check alone do not
   establish acceptance. Never replay a reserved pair or delete its markers.
6. Only after acceptance, deliberately choose the **then-current UTC instant**
   and set `CENTRAL_REVIEW_SINCE` in strict `YYYY-MM-DDTHH:MM:SSZ` format. Do not
   reuse a historical cutoff, backdate it to include acceptance/backlog PRs, or
   replay earlier work. Read back that exact cutoff, then set
   `CENTRAL_REVIEW_ENABLED` to exactly `true` and read it back. Config gates,
   accepted fresh real-PR/ledger evidence and this final runtime gate are separate
   requirements. Leave the runtime variable unset or `false` until then.

## Discovery and execution

The draft workflow defines a 30-minute schedule and permits manual dispatch without
inputs. The job requires the configured hub, `refs/heads/main`, and the runtime
enable variable. It checks out immutable `github.sha`; there is no arbitrary
manual source ref. One `central-review-hub` concurrency group serializes runs
without cancellation on Ubuntu 24.04, with a 20-minute job timeout.

Discovery uses installation repositories and open PRs, excluding the hub,
private, forked, archived or disabled repositories, foreign owners, draft PRs,
fork/deleted heads, and bases other than each target's default branch. A PR must
have `updated_at` **strictly after** the cutoff. Discovery scans open PRs and then
filters by `updated_at`; there is no historical backlog review processing. A PR
last updated at or before activation is skipped. An older PR updated
after activation can qualify. Do not move the cutoff backward to replay history.
New eligible repositories require no per-target setup under the all-repository
installation.

Current default-branch tip and PR head are rechecked. Both lanes receive the same
immutable merge-base/head source diff; receipts also bind the discovered base
tip and diff hash. Source blobs are inspected without a target checkout, build,
dependency installation, hook, test, or PR code execution. Alibaba OpenCodeReview
v1.13.7 is downloaded over HTTPS and SHA-256 checked. It uses trusted source-only
scaffolding. Hidden path components, components containing `opencodereview`, and
`config.json`/`rule.json` control paths are rejected rather than silently omitted.
Global OCR control files also block preflight. No target workflow or key is copied.

Only bounded source/diff inputs go to the reviewer; no Actions source/artifact
uploads or raw source/provider logs are retained. Target Checks receive bounded,
escaped, untrusted finding previews; the hub console receives aggregate status
only. Do not publish operational transcripts, credentials or account evidence.

## Reservations and retained state

The current limits are **2 PR reservations per run and 6 per UTC day**, across
targets and across hub source revisions. Before source collection, an append-only
reservation is written and read back from Checks on the fixed hub anchor commit,
then a target receipt is written and read back. Each lane's unknown marker is
read back before invocation. Retain that anchor and the complete check ledger;
unreadable, malformed, missing-anchor, or truncated state blocks paid work.

Every reservation consumes capacity, including failed, interrupted and unknown
outcomes. Source-entry or extraction failure records a failed target receipt with
`SOURCE_BLOCKED_OR_UNKNOWN`, consumes the reservation, and calls no lanes. The run
continues to the next eligible candidate; later polls skip that same pair to avoid
repeat starvation. Ambiguous ledger or receipt writes/reads still stop the whole
run. Daily accounting includes all statuses and conservatively counts both
Check start and reservation dates across midnight. A lane cannot start on a new
UTC day using the preceding day's reservation. Deduplication uses target
repository/base-tip/head and target receipts, independently of hub checkout SHA.
There are no refunds, automatic retries, reconciliation, or replay after repair.
A lost write acknowledgment stops the run; do not delete checks to recover slots.

Each reserved PR permits up to **8 Alibaba HTTP attempts plus 1 Cloudflare-guided
HTTP attempt**, sequentially using Xiaomi `mimo-v2.6-pro`. These are request and
reservation ceilings, **not a dollar cap**; token usage, billing, and unknown
responses still matter. Cloudflare supplies methodology, not the model provider.
Two lanes on the same provider/model do not establish independence. Findings need
resolution, required independent-provider evidence, and human merge authority.
`BOTH_RECORDED_NOT_ACCEPTED` and even a successful Check do not authorize merge.
Changed or unverifiable bindings fail the receipt.

## Limits, stop procedure and remaining gaps

Discovery caps are 250 installation repositories and 100 open PRs per repository;
the hub ledger and each target's matching receipts are capped at 1,000 entries.
Incomplete pagination or exceeded caps fail closed before further paid work.
Source extraction retains the existing 20-path, 64-KiB diff/snapshot, regular-file,
binary and symlink rejection gates. Full Git fetch can download all history and
blobs reachable from both commits. **256 MiB is an observed scratch-disk bound,
not a hard network or disk ceiling**: a pack can exceed it between polls. A hard
ceiling requires runner-level disk/network enforcement, which is not supplied
here. Time/output limits do not substitute for that control.

To stop future work, set the hub's `CENTRAL_REVIEW_ENABLED` to `false`. For a
persistent code-policy stop, return both config gates to `false` through central
review. An already running job retains its starting environment; disabling the
variable does not interrupt it. Avoid cancelling a potentially billed lane;
interruption remains unknown and its reservation stays consumed. Preserve all
receipts and ledger state when stopping or restarting; restart requires an
accepted policy and a deliberate cutoff, without historical replay.

Before this 2026-11-12 draft, unsupported Markdown handling in the Alibaba adapter
was recorded as unresolved; failed lanes consumed their reservations. That
historical observation is not a diagnosis of any particular failed run. Real-PR
acceptance, durable GitHub behavior, App installation scope, and the full-fetch
resource controls remain unvalidated.

## Static repair — 2026-11-12

Read-only inspection used the local pinned OCR source at
`b1dcffb0729f3f2e3e47170968a5014a2e035580` (v1.13.7).
Its [flags](https://github.com/alibaba/open-code-review/blob/b1dcffb0729f3f2e3e47170968a5014a2e035580/cmd/opencodereview/shared_flags.go)
support `--rule`; `--no-filter` affects comment post-filtering, not file selection.
The [rule loader](https://github.com/alibaba/open-code-review/blob/b1dcffb0729f3f2e3e47170968a5014a2e035580/internal/config/rules/system_rules.go)
supports an `include` glob. The adapter now writes only
`{"include":["**/*.md"]}` to a trusted scratch rule file **outside** the source
snapshot and passes it via `--rule`. No target-derived policy or review-rule text
is added. In [selection](https://github.com/alibaba/open-code-review/blob/b1dcffb0729f3f2e3e47170968a5014a2e035580/internal/agent/selection.go),
binary and secret-path rejection precede includes; deletion and size gates still
apply. Other extensions retain their default selection rules. Full snapshot
file-count coverage, expected model, completed response/output, no warnings and
valid findings remain required; selection wiring alone proves no completion.

Both adapters now raise typed failures with a fixed stopping-stage vocabulary.
Failed central receipts retain only that stage, CLI exit code (integer from
−255 to 255, otherwise `null`), HTTP attempts/completed-response counts (0–8 for
Alibaba, 0–1 for the guidance lane, otherwise `unknown`), boolean halted state or
`unknown`, and safe usage. Usage keeps only `prompt_tokens`, `completion_tokens`
and `total_tokens`, each an integer from 0 to 1,000,000,000 or `unknown`, in at most
8/1 rows respectively. Missing usage is `unknown`; absent rows do not imply zero
cost. Alibaba counters are sampled after relay cleanup; an unsettled or lost
worker has unknown counters. Generic exceptions have unknown metadata, never
invented zeroes. The worker and receipt writer reproject failures through this
allowlist; exception text, paths, stderr, provider text, credentials and headers
are excluded from diagnostics. Stages identify stopping points, not root causes.
Completed central receipts also retain bounded completion/halted/exit metadata.

Exactly three mocked cases are authored in
[`tests/check_central_review_live_acceptance.py`](../tests/check_central_review_live_acceptance.py):
`test_trusted_markdown_rule_wiring`, `test_safe_alibaba_failure_diagnostics` and
`test_central_failed_receipt_persists_safe_metadata`. At the initial static repair,
**none had been run**. The subsequently recorded mocked result is **3 PASS /
1 invocation / 0.005s**, not live-provider or real-PR acceptance. The earlier five
central cases used mocked API/source/lane/preflight dependencies and remain
historical evidence only. No cases were rerun for this readiness change; authoring
cases adds no execution budget. No workflow/config/auth/settings/hooks or
activation changed.

Remaining acceptance requires separately authorized evaluation and current-head
external review of this repair, finding resolution, and installation on the
trusted base. A bounded real PR must demonstrate **actual-source completion in
both lanes** on the same immutable base/head/diff binding with the recorded actual
provider/model. Read back the final target Check and hub reservation from Checks,
verify the exact current binding and retained diagnostics, and establish durable
deduplication against both the hub ledger and target receipts, including failed
or unknown pairs across hub revisions. Reconcile existing consumed reservations
before any new paid work; never replay a reserved pair or delete its markers.
Mocks, static inspection and a successful Check alone do not satisfy these gates.
The normal [dual-review contract](dual-review.md), required provider independence,
human acceptance and merge gates still apply. Central recurring work stays disabled.

## Offline recurring-start readiness — 2026-11-12

[`tools/central_review_readiness.py`](../tools/central_review_readiness.py) is a
read-only offline reporter with no caller flags. It reads only the fixed local
central config/workflow and bounded local Git metadata/diff for `origin/main` and
`HEAD`, using their immutable merge-base/head. It never fetches, reads credentials,
invokes reviewers, writes files or changes gates. The remote-tracking ref can be
stale; uncommitted edits and fresh target PR state are outside this measurement.

It reports changed-path count, diff bytes, and the summed before-plus-after blob
sizes against fixed **20 path / 65,536 diff bytes / 65,536 snapshot bytes** caps.
Oversize, missing refs, unsupported blobs or bounded-read failures stay blocked;
unavailable measurements are `null`, with a lower bound for a truncated diff.
Over-20-path input is not traversed for blob totals. No exclusions or cap override
are offered. Passing local size caps is only a size observation, not full source
preflight, merge approval, paid allowance, target acceptance or enable authority.

The report always keeps **human merge**, **new paid allowance**, **fresh real-PR
Check/ledger acceptance**, and **runtime enable** as separate pending external
stages, regardless of observed config values. Two offline cases are authored in
[`tests/check_central_review_readiness.py`](../tests/check_central_review_readiness.py)
and **not run**. One read-only reporter invocation observed local
`origin/main`/merge-base `7eabdf4973fdf06f768319020a60311275d6b7b2` to
`HEAD` `8e53c1e79de5f6ce690cc8a72072f974b3857acd`: **5 paths, 54,178 diff
bytes, 170,398 before-plus-after blob bytes**. The snapshot cap therefore keeps
this input **BLOCKED**; no cap or exclusion changed. This observation excludes
the current uncommitted repair and is not a test or fresh real-target acceptance.
The required current-head dual-review lanes remain unexecuted: no external route
or new paid allowance was used. The activation order above remains pending.
