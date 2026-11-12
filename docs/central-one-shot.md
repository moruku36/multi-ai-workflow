# Signed one-target central review — inactive source draft

[日本語](central-one-shot.ja.md)

## Observed state — 2026-11-12

| Layer | State |
| --- | --- |
| Operator signature, launcher provenance, common target lifecycle, sender caps | Source draft implemented; statically reviewed, not behavior-verified |
| Focused offline verification | Five cases authored in tests/check_one_shot_integration.py; UNEXECUTED |
| Trust-root provisioning | Empty checked-in key list; no operational keys generated or installed |
| Workflow deployment / real target acceptance / recurring activation | Not performed |
| Independent two-lane code review / human merge | Not completed for this draft |

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
  positive and at most one hour; now must be within it.
- lane_attempt_limits: Alibaba 1–8; Cloudflare 1.

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

Hub.prepare_one_shot authenticates evidence and launcher before preflight.
Hub.run_one_shot passes only the signed target into _run_targets; it never
discovers other repositories. Recurring run uses the SAME _run_targets:

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

The signed UTC expiry is rechecked before reservations and lanes, converted
to a bounded monotonic deadline, enforced before each actual HTTP send, and
also bounds the lane worker lifetime. In-flight responses can become unknown;
an expiry does not refund them or authorize a resend. No output-byte guard
is described as a provider-side token/dollar limit.

## Verification still required

The five authored cases cover real local Ed25519 verification/tampering/empty
roots, launcher claim rejection and environment-only denial, common-ledger
ordering/replay/cap propagation, lost reservation acknowledgment, and actual
sender caps/failure charging/expiry. All are UNEXECUTED. Local API/transport
fixtures are not GitHub OIDC or provider acceptance. Real JWKS/JWT compatibility,
actual concurrency and authenticated workflow execution require separate
bounded acceptance after infrastructure recovery and appropriate remaining
authorization. Never silently consume or reset the earlier seven-case batch.

The large-source first independent review route and its existing size policy
remain unresolved. Do not trigger a known oversized paid automatic review
merely to publish this draft. No activation, key provisioning, workflow dispatch,
live paid review, merge or production configuration change is included.
