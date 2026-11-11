# Central review hub

[日本語](central-review-hub.ja.md)

**Inactive draft; offline checks passed.** The five mocked offline test cases
passed in one invocation. The workflow and live integration have not been accepted
on a real PR. Both `enabled` and
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
4. Set hub variable `CENTRAL_REVIEW_SINCE` to the chosen activation instant in
   strict UTC format `YYYY-MM-DDTHH:MM:SSZ`, at or before the current instant.
   Then set hub variable `CENTRAL_REVIEW_ENABLED` to exactly `true`. Config gates,
   valid cutoff and runtime gate are all required. Leave the variable unset or
   `false` until activation is accepted.

## Discovery and execution

The workflow schedules every 30 minutes and permits manual dispatch without
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
There are no refunds, automatic retries, reconciliation, or Markdown repair.
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

Unsupported Markdown handling in the existing Alibaba adapter is **still not
fixed**; such a lane may fail with its reservation consumed. The five offline
cases passed with every API/source/lane/preflight dependency mocked;
this does not establish real provider execution or live integration acceptance. Real-PR acceptance, durable GitHub
behavior, App installation scope, and the full-fetch resource controls remain
unvalidated. The normal [dual-review contract](dual-review.md) and human,
independence and merge gates still apply.
