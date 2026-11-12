# Signed one-target central review — inactive source draft

[日本語](central-one-shot.ja.md)

## Observed state — 2026-11-12

| Layer | State |
| --- | --- |
| Operator signature, launcher provenance, common target lifecycle, sender caps | Source draft plus three bounded review fixes; new behavior UNEXECUTED |
| Historical offline verification | Five cases in tests/check_one_shot_integration.py succeeded in CI run [43169607402](https://github.com/moruku36/multi-ai-workflow/actions/runs/43169607402) before these fixes |
| New review regressions | Exactly three focused scenarios authored (no parameterized subcases) in tests/check_one_shot_review_regressions.py; UNEXECUTED |
| Trust-root provisioning | Empty checked-in key list; no operational keys generated or installed |
| Live OIDC / external signing and custody / concurrency acceptance | UNACCEPTED; historical offline CI does not establish these |
| Workflow deployment / real target acceptance / recurring activation | Not performed |
| Review / human merge | Fresh source review of PR53 HEAD 0203ada2feb26fffa85dbfde0d726757775e609a completed; acceptance of these new fixes and human merge remain pending |

The earlier 2026-11-12 draft recorded the five authored integration cases as
UNEXECUTED. That historical observation is superseded for those five by the CI
success above, not for the new three or for live acceptance. This bounded fix
task ran no tests, imports, builds, syntax executables, provider calls or probes.

This is product code, not a change to OpenClaw execution permissions. It does not
repair the host approval-binding blocker or reopen historical test/call budgets.
Do not equate an exit, signature, Check success, or source draft with review
quality, independent provider acceptance, delivery or merge authority.

## 1. Operator evidence

tools/central_one_shot_auth.py verifies detached Ed25519 signatures with the fixed
/usr/bin/openssl binary (OpenSSL 3 required). There is no signer or private-key
loader. Public trust roots come only from config/central-one-shot-trust.json in
the trusted controller checkout. An empty list blocks one-shot execution.

Envelope encoding is exact canonical ASCII JSON, with sorted keys, no optional
whitespace or trailing newline, and Python ensure_ascii escaping. It has exactly
payload and signature. signature is canonical standard-base64 of 64 bytes.

Signed bytes are the byte domain
central-review-hub NUL one-shot NUL v1 NUL followed by canonical(payload).
Payload fields are exactly:

- schema_version: integer 1; domain: central-review-hub/one-shot/v1.
- issuer and key_id: public-safe lowercase identifier strings, 1–64 characters.
- authorization: exactly kind=one_target_dual_review, targets=1,
  reruns=false, refunds=false, with strict integer/boolean types.
- repository, pr, base, head and controller_revision: one eligible owner target,
  excluding the hub, with fixed 40-character lowercase commit SHAs.
- eligible_since and expires_at: UTC second-resolution strings. The window is
  the TOTAL expires_at minus eligible_since interval, strictly positive and at
  most 3600 seconds; a short remaining lifetime cannot excuse a longer window.
  now must satisfy eligible_since <= now < expires_at.
- lane_attempt_limits: strict integers, Alibaba 1–8 and Cloudflare exactly 1,
  checked before any reservation. Zero is invalid signed authority; lower-level
  sender zero-cap support remains available for its own fail-closed behavior.

The envelope is capped at 8192 bytes. Duplicate/extra fields and non-finite
numbers are rejected. Payload changes invalidate the signature. A digest,
manifest boolean, request-supplied key or injected callback is not authority.

Trust policy schema is exactly schema_version=1 and keys, at most 16 unique
(issuer,key_id) entries. Each entry has issuer, key_id, algorithm=Ed25519 and
public_key, canonical base64 of the 32 raw public-key bytes. Policy edits must
follow independent review and the existing human merge gate. Keep private keys
outside the repository and workflow; external signing and custody remain
operator deployment prerequisites. No such setup occurred in this work.

controller_revision is independently derived from a clean Git HEAD with fixed
system Git and a restricted environment, then compared with signed and GitHub
claims. Sign for the actual reviewed main revision after any policy changes;
a signature for a feature-branch SHA or a former main is not transferable.

## 2. Trusted, serialized launcher and shared lifecycle

The sole production integration is .github/workflows/central-review-hub.yml on
the fixed hub repository/main. Its existing workflow-wide concurrency group is
central-review-hub with cancel-in-progress=false. One-shot is an optional
workflow_dispatch input named one_shot_envelope in the SAME job, not a second
launcher, separate lock, local paid command, enabled-flag override or scheduler.
Recurring activation flags retain their disabled defaults.

tools/central_one_shot_provenance.py verifies the GitHub OIDC JWT signature
(RS256 via OpenSSL and GitHub's TLS-fetched JWKS certificate) and exact issuer,
audience, repository/owner, main ref, workflow path, source/workflow revision,
hosted-runner, event and run claims. The one-shot audience includes the SHA256
of the exact signed envelope; recurring uses a different audience. One-shot
requires run_attempt=1, so rerunning an old job is not an approval route.
Environment strings only locate the runner capability and are compared with
authenticated claims; GITHUB_ACTIONS=true alone grants nothing.

Deployment trusts GitHub TLS/JWKS, OIDC issuance, hosted-runner isolation and
the reviewed main workflow retaining this concurrency contract. It is not a
defense against stolen runner capabilities, operator private keys or control
of trusted main. Missing/changed claims, certificate schema, unsupported
OpenSSL, custom OIDC subjects or runner service host contracts block rather
than fall back. The added job-level id-token:write is SOURCE ONLY until this
workflow is reviewed and deployed. Actual GitHub claim/host compatibility has
not been accepted on a real run. No JWT/capability/raw signature is published.

Hub.prepare_one_shot samples monotonic time before UTC and envelope validation.
Initial payload validation freezes one deadline from those samples, capped by
the run deadline, before signature verification can consume time. Only successful
authentication returns the payload and this separate local deadline; no unsigned
field is added to the signed payload. Launcher verification uses that deadline.
Hub.run_one_shot passes the signed target and explicit frozen deadline into
_run_targets; it never discovers other repositories. Recurring behavior is
unchanged and uses the SAME _run_targets:

1. Verify current target binding, complete ledger, dedup and existing day/run caps.
2. Consume and read back the global reservation; unknown ACK stops without retry.
3. Recheck target reservation, create and read back its receipt.
4. Obtain bounded immutable sources without executing target code.
5. Recheck target/day/deadline and durably record unknown before each provider lane.
6. Persist safe results with unchanged staleness, quality and human merge gates.

Existing unknown reservations are never refunded. Ineligible/stale/duplicate
one-shot targets block rather than silently reporting successful completion.
The legacy validate_one_shot remains a READ-ONLY proposal validator for old
offline checks; it is not used to authenticate production paid execution.
GitHub concurrency can replace pending runs; a dispatch acknowledgment is not
an execution receipt, and an expired queued authorization does not renew itself.

## 3. HTTP attempt and payload limits

Signed caps are passed through Hub → real_lane → child worker → Alibaba relay
and Cloudflare sender. The effective cap never exceeds the existing lane cap.
Both actual sender paths reserve serialized bytes before HTTP, count failed
sends, and never refund. Cloudflare retains its 196608-byte request ceiling;
source/diff/snapshot ceilings remain 65536 and Alibaba's existing cumulative
envelope remains unchanged. These are not monetary ceilings.

UTC active checks remain before both reservations and every lane. The SAME
initially frozen monotonic bound is also enforced there and after the durable
lane marker, then passed through real_lane and its worker to both actual senders.
Neither verification/preflight delay nor UTC rollback recalculates a later bound.
The sender checks it before HTTP, and it also bounds the lane worker lifetime.
In-flight responses can become unknown;
an expiry does not refund them or authorize a resend. No output-byte guard
is described as a provider-side token/dollar limit.

## Verification still required

The historical five cases cover real local Ed25519 verification/tampering/empty
roots, launcher claim rejection and environment-only denial, common-ledger
ordering/replay/cap propagation, lost reservation acknowledgment, and actual
sender caps/failure charging/expiry. Their CI success at run 43169607402 is
historical evidence for the earlier implementation, not execution of these fixes.

The new, UNEXECUTED methods are:

- test_frozen_deadline_survives_delay_and_clock_rollback
- test_signed_lane_caps_reject_zero_before_reservations
- test_total_authorization_window_is_positive_and_at_most_one_hour

These three scenarios cover clock rollback between lanes, a zero Alibaba cap,
and an overlong total interval with only one second remaining. They exercise
the real payload/lifecycle/sender guards with offline fixtures and
time/transport mocks, without invoking OpenSSL, a target process or a network.
.github/workflows/one-shot-offline.yml selects ONLY these three methods on PR
synchronize, retaining the checkout pin, read-only permissions and credential
isolation. It does not rerun the historical five, the old seven, or a push/main
duplicate. This edit does not execute or dispatch that workflow.

Local fixtures are not GitHub OIDC or provider acceptance. Live JWKS/JWT
compatibility, external signing/custody, actual concurrency and authenticated
workflow execution remain UNACCEPTED and require separate bounded acceptance
with appropriate authorization. Never consume or reset the earlier seven-case
batch. No new independent two-lane acceptance of these fixes is claimed.

The large-source first independent review route and its existing size policy
remain unresolved. Do not trigger a known oversized paid automatic review
merely to publish this draft. No activation, key provisioning, workflow dispatch,
live paid review, merge or production configuration change is included.
