# Review preflight follow-up

[日本語](review-preflight.ja.md)

2026-11-12: PR53 follow-up, base `87a22a5`. Bounded immutable fetch/collect now
precedes durable reserve; both lanes remain after reserve. Report initialization
precedes preflight; finally retains it. `PREFLIGHT_REJECTED` makes no reservation;
`RESERVATION_FAILED_OR_UNKNOWN` stops all lanes. Diagnostics exclude exception
text, secrets, source and model content. Existing checks/reservations stay
untouched; historical unknown outcomes, attempts and costs stay unknown. No replay.

SHA/diff binding and byte/token/timeout/concurrency/paid limits are unchanged.
No central/OIDC/signing/activation/key/policy changes; existing review/merge gates apply.

Two independent unittest methods: oversized collect rejection and ready-path
ordering/bindings; authored **UNEXECUTED**, no subcases. External I/O/API/crypto/
providers are mocked; only temporary receipt I/O is real. Branch-only CI selects
these two on PR opened/synchronize. Trial: 8 cases / 2 CI invocations; two remain
for one parent-arranged CI invocation, no reruns. Zero tests/source programs run.
Both real-diff reviews and live acceptance remain pending; mocks prove neither.
