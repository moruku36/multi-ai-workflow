# Repository inventory ledger (P2a)

[日本語](review-inventory.ja.md) · Design: [global review design](global-review-design.ja.md) (§4, §5, §6, §9)

> **Status: authored, not executed; disconnected, unauthenticated, pure shadow module.**
> Standalone and offline: no network, no change to the hub, workflows or config, no
> activation. Facts, owner metadata and trust flags are bare caller claims, not
> authenticated enforcement, so `enforced` means *claimed* enforced and is no proof
> that any repository is protected. Tests are written but not run.

## Purpose

One ledger entry per repository, so excluded, unverified, private, fork, archived
and foreign repositories stay visible. Unknown or unprotected is never a pass.

## Files

- `tools/review_inventory.py`: pure functions over already-fetched records and facts.
- `tests/check_review_inventory.py`: ten synthetic cases (authored only).

Out of scope: fetching, pagination reading, webhooks, checks, protection readback,
PR-level coverage, any change to `tools/central_review_hub.py`.

## Entries and classification

Fields: `key`, `repository_id`, `full_name`, `owner`, `visibility`, `fork`,
`archived`, `disabled`, `default_branch`, `installation_id`, `consent`,
`enrollment`, `protection`, `coverage_class`, `reasons`, `enforced`,
`operator_action`. Unknown values stay `null`/`unknown`.

| coverage_class | meaning |
|---|---|
| `eligible` | public, same owner, non-fork, active, installation known |
| `manual_required` | private, fork or no installation; human path only |
| `excluded` | foreign owner, the hub itself, archived or disabled |
| `unverified` | malformed or duplicate record, or malformed facts |

Reasons: `invalid_record`, `invalid_facts`, `duplicate_repository_id`,
`not_owner_managed`, `hub_self_excluded`, `archived`, `disabled`,
`private_consent_pending`, `private_unsupported`, `fork_manual_required`,
`installation_missing`. Private repositories are never sent externally here.

Enrollment: `discovered → consent_pending → configured → protection_verified →
acceptance_pending → enforced`, plus `degraded`. `enforced` needs eligible
coverage, `configured`, protection claimed verified and acceptance `passed`; facts
that skip a step are `invalid_facts`; progress on an ineligible repository is
`degraded`.

## Completeness and scope

Listing completeness and derived owner completeness. `complete`: listing and record
integrity only. `owner_complete`: derived, `complete` AND an explicit owner-universe
reconciliation (reasons in `owner_incomplete_reasons`, separate from
`incomplete_reasons`). `all_enforced` needs `owner_complete`, a non-empty ledger and
every entry enforced.

`complete` is false on truncated or unknown pagination (`truncated=None`), count
reaching `limit`, any malformed row or facts, malformed or unmatched facts keys,
duplicate IDs or an invalid scope. `limit` must be a positive int, else
`ValueError`.

`scope` is required. `owner`: the list is the full owner listing, its pagination
state is `truncated`; `owner_ids`/`owner_truncated` are installation-only and
rejected here (`owner_metadata_not_allowed`). `installation`: a subset;
owner-complete only if the caller passes `owner_ids` (a list, tuple, set or
frozenset of distinct positive ints from an independent owner reader) that equals
the valid listed IDs exactly (missing, extra and empty-versus-nonempty are all
mismatches) AND `owner_truncated` is literally `False` (`None`, `True`, `0` are
not). A clean subset without these stays `complete` but not `owner_complete`. An
empty complete ledger is never `all_enforced`. All of this is unauthenticated.

Facts keys must be positive non-bool ints; others, including `True`, are never
attached. Duplicate IDs: every member is kept with sanitized identity, forced
`unverified`, never enforced. Identity: `full_name` prefix must equal
`owner.login` (case-insensitive); a foreign owner is `not_owner_managed`. Default
branch: non-empty, control-free, at most 250 characters.

## Privacy

By default `public_view()` emits no names, repository IDs or ID-derived keys; rows
get content-ordered `restricted:N` keys. Only with `visibility_trusted=True`
(literal; a caller claim of a trusted visibility readback, not credentials or
release authority) do valid, non-duplicate public rows show key, ID and name.
Private, unknown, malformed and every unresolved duplicate row never do; their
identities stay in the private ledger.

## Limits

- Input, facts and trust flags are unauthenticated caller claims; a later,
  separately reviewed trusted reader must supply them. Nothing here enforces anything.
- Not done: webhook ingress, protection audit, job schema, aggregate gate.
- Tests are unexecuted; running them needs an explicit new budget.
