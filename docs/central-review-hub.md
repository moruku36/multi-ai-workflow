# Central review hub

[日本語](central-review-hub.ja.md)

[Signed one-shot preparation](central-one-shot.md) is separate from recurring
authorization. The linked [2026-11-12 draft](bounded-hub-draft.md) is historical.

**Dormant advisory candidate; offline evidence only.** The recurring token is
scoped to two repositories: `moruku36/multi-ai-workflow` (ID 1365934149) for the
shared reservation ledger and `moruku36/local-ai-sidekick` (ID 1369269341) as
the only review target. Neither recurring nor signed one-shot execution has live
acceptance. Both `enabled` and `paid_execution_authorized` in the
[central config](../config/central-review-hub.json) default to `false`, and the
[one-shot trust list](../config/central-one-shot-trust.json) is empty. The
historical mock results below are not hosted or real-PR acceptance.

## One-time central setup

1. For this cohort, use one installation on the configured owner with **Only
   select repositories**: the hub and Sidekick. Do not grant **All repositories**.
   Confirm effective repository membership, accepted permissions and that the
   installation is not suspended; reconcile any pending grant changes. The App
   needs **Contents: read**, **Pull requests: read**, **Checks: read and write**
   and GitHub's mandatory Metadata read. It needs no Actions, administration or
   source write access. The workflow narrows the **minted token**, not the App's
   installation grants or what its private key can authorize across its
   installations. Token readback does not audit those underlying grants.
2. In the hub alone, provision Actions variable `APP_ID` and secrets
   `APP_PRIVATE_KEY` and `MIMO_API_KEY`. Do not copy workflows or keys to the target.
   The pinned App-token action explicitly requests the two repository names
   and Contents read, Pull requests read and Checks write. `GITHUB_TOKEN` is
   limited to Contents read; the scoped App token supplies cross-repository
   Checks writes. The App key is separate from the one-shot operator signing
   key, which stays outside the repository and workflow.
3. Review the trusted workflow, controller, config, exact cohort, provider source
   disclosure, reservation limits and separate recurring paid authority. Resolve
   findings and meet existing review and human merge gates on trusted `main`.
   Keep the runtime gate off during preparation. Both recurring config gates must
   be explicitly authorized and set to `true` by reviewed policy before recurring
   activation; the source draft does not grant that authority.
4. For fresh real-PR acceptance without enabling recurring work, the signed
   one-shot path requires a new, explicit paid allowance for one run, external
   signer custody and reviewed public-key trust, and a fresh, unreserved Sidekick
   PR bound to the reviewed/landed immutable controller revision and base/head/diff.
   Reconcile consumed reservations first and keep the limits of 20 paths and
   65,536 bytes each for the diff and total before-plus-after blobs. Do not raise
   limits or omit paths. Verify hosted launcher/OIDC and scoped token issuance;
   complete both actual-source lanes, record their actual provider/model, and
   resolve findings under the existing independence and human acceptance gates.
   The route is not usable with the empty trust list; local evidence and caller
   flags do not authorize spend.
5. Read back the final target Check/receipt and hub reservation/ledger. Confirm
   the exact current base/head/diff, completion and safe diagnostics, retained
   consumed failures/unknowns, and durable deduplication across hub revisions.
   Accept those readbacks explicitly; mocks or a successful Check alone do not
   establish acceptance. Never replay a reserved pair or delete its markers.
6. Only after those readbacks are accepted and recurring execution is separately
   authorized, set `CENTRAL_REVIEW_SINCE` to the **then-current UTC instant** in
   strict `YYYY-MM-DDTHH:MM:SSZ` format and read it back. Do not reuse or
   backdate the cutoff to include the acceptance PR or backlog. Set
   `CENTRAL_REVIEW_ENABLED` to exactly `true` and read it back only for
   the authorized cohort activation; leave it unset or `false` until then.
   Hosted recurring token mint, exact scope readback and launcher/OIDC must
   succeed on the reviewed revision before recurring operation is accepted.
   One-shot acceptance does not establish any of those recurring results.

## Discovery and execution

Recurring mode is the 30-minute schedule or manual dispatch with an empty
`one_shot_envelope`. The job requires the configured hub and `refs/heads/main`
and checks out immutable `github.sha`. Before minting a recurring token, the
workflow checks the exact scope, both config gates, the runtime gate and a valid
non-future UTC cutoff without App or provider credentials. After minting and
before CLI download or controller execution, a token-only readback requires a
complete REST listing of exactly the two named repositories and stable IDs,
explicit public visibility, the configured owner, and an eligible Sidekick
target. Missing, extra, substituted or incomplete results stop the run. The
controller separately verifies hosted launcher provenance.

A non-empty `one_shot_envelope` selects the signed one-shot path. It verifies
the exact envelope and GitHub-hosted OIDC provenance before minting its own
hub-plus-Sidekick token; it reviews only the authorized target PR and never
falls back to recurring discovery even on failure. Both modes share the
`central-review-hub` concurrency group and ledger, without cancellation, on
Ubuntu 24.04 with a 20-minute job timeout.

Recurring discovery uses the verified token scope. It excludes the hub,
private, forked, archived or disabled repositories, foreign owners, draft PRs,
fork/deleted heads, and bases other than the target's default branch. A PR must
have `updated_at` **strictly after** the cutoff. Discovery filters open PRs;
it does not process historical backlog. An older PR updated after activation
can qualify. Do not move the cutoff backward. No repository is enrolled
automatically. Expansion requires a separately reviewed cohort with verified
ownership, eligibility and App membership; preserve the shared ledger and limits.

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
The Hub produces advisory Checks only, not merge enforcement. Receipts set
`merge_authorized=false` and `review_quality_accepted=false`.
`BOTH_RECORDED_NOT_ACCEPTED` and even a successful Check do not authorize merge.
Existing human merge gates remain in force. Changed or unverifiable bindings
fail the receipt.

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
acceptance, durable GitHub behavior, effective App grants, hosted token issuance
and scope readback, launcher/OIDC, and full-fetch resource controls remain
unvalidated.

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
