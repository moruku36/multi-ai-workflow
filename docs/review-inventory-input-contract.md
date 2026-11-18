# Review inventory snapshot input contract

The disconnected adapter `tools/review_inventory_snapshot.py` validates an
already-fetched snapshot and delegates to `review_inventory.build_inventory`
(schema 3). It does no IO, clock reads, fetches or hub imports.

## Envelope

Exactly these keys (`digest` optional): `hub` (owner/name), `owner`
(`{id, login}`), `acquisition` (`source` offline_fixture or
recorded_api_response, `scope` owner or installation, `observed_at`
`YYYY-MM-DDTHH:MM:SSZ`, `owner_listing {complete, truncated}`),
`owner_repositories` (list for scope owner, else null), `installation` (null or
`{id, status, account_id, account_login, observed_at, complete, truncated,
repositories}`), `facts` (list of `{repository_id, facts}`).

## Fail-closed

Structural faults raise ValueError with a fixed code (envelope, hub, owner,
acquisition, time, rows, facts, duplicate facts, scope mismatch, installation,
digest mismatch, too large, not json). Aliased or cyclic containers, floats,
tuples and oversize values are rejected.

Incomplete snapshots return status `incomplete` with reasons. Installation
access is granted only in state `bound`: active, account matching owner,
observed_at equal to the acquisition time, complete, below the row limit.
Other states: absent, not_active, unknown_status, mismatch, stale, incomplete.
A row is kept apart (quarantined) unless it is unique, valid and equal to the
sole owner row with the same ID. Rows of different IDs sharing a case-insensitive
valid `full_name` conflict: no ID of the group gets installation access and the
result is incomplete (`installation_rows_conflict`). Rows whose `owner.login`
differs from the target owner are foreign: they stay visible, never count as
onboarded, get no installation access and make the result incomplete
(`owner_rows_foreign`), including in installation-only scope. An explicit
visibility that contradicts the private flag makes the row invalid. A supplied `installation_id` fact never grants
access and conflicts degrade the result.

## Bounds and digest

At most 250 rows (union included), 20000 nodes per tree and per container,
depth 8, strings 300 characters, and no more than the envelope key set at the
root. Status counts use the retained rows as denominator; the 250-row bound is a
validity limit, not a count of onboarded repositories. The digest is sha256 of sorted-key compact
ASCII JSON without the digest key. It labels data; it is not a signature.

## Semantics

All labels, times and digests are unauthenticated caller claims, never proof of
coverage or protection. The `public` view is redacted: no IDs, names, digest or
times, and visibility is untrusted.

## Entry point

`review_inventory_snapshot.adapt_snapshot(envelope)` returns a dict with
`status`, `installation_state`, `adapter_reasons`, the private `ledger` and the
redacted `public` view.

## Invocation

`python3 -I -S -B tests/check_review_inventory_snapshot.py`
