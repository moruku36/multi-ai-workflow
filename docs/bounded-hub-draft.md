# Bounded acceptance draft — 2026-11-12

[日本語](bounded-hub-draft.ja.md)

Source only; recurring config and flags remain disabled. `Hub.prepare_one_shot`
validates one operator proposal bound to repository/PR/base/head, expiry (at most
one hour ahead), trusted launcher revision, evidence digest and per-lane attempt
limits. It reads the existing reservation ledger, eligibility/current bindings,
daily/run limits and target receipts. Every prior reservation/unknown still
suppresses duplicates. The hub itself and all other exclusions remain excluded.
The returned reservation and target receipt identities use the existing namespace.

No independent operator evidence verifier or trusted one-shot launcher is available.
An evidence digest establishes consistency only. `run_one_shot` refuses execution;
no manifest boolean, injected callback or request field authorizes spend. A future
trusted integration must authenticate evidence independently, enforce its controller
revision and attempt limits inside each relay, serialize with the same hub-wide
concurrency group and reuse the exact global-reservation → target-receipt → durable
unknown → lane sequence. Recheck current bindings and expiry before every paid lane.
No force, reset, refund or unknown-result replay route is added.

`automatic_dual_review.py` separates diff bytes (65,536), cumulative snapshot bytes
(65,536), Alibaba serialized per-request bytes (65,536), cumulative outgoing bytes
for Alibaba (524,288), calls (Alibaba at most eight; guidance lane one), output tokens
(2,048) and the existing independent provider-response/output-file caps. Outgoing
bytes are charged before forwarding, including failed sends. Guidance and JSON
escaping count toward the actual body cap. The former guidance-body 196,608 check
is preserved, with a one-call cumulative cap of the same size. The Alibaba
cumulative cap equals its existing eight-request maximum envelope; neither lane's
per-request ceiling is expanded. Even a collectable diff may be unsendable.

No existing trusted configuration authorizes larger sources. Larger-source opt-in
is deliberately unavailable. A future separately reviewed trusted policy would
need explicit independent limits for collection, serialized body, cumulative bytes,
calls and output, bound to authorization and controller revision; source size alone
must never raise a request limit. PR52 merge is independently verified at main c2a49f87e13a9a7c8eea2a3299a3bb8aba90cb05, is an excluded
hub target and cannot automatically review itself under unchanged caps.

Three offline cases authored, **NOT RUN**. No tests, imports, compilation, builds,
readiness scripts, network, paid reviews or target code executed. Live authority,
bounded acceptance, same immutable base/head dual review, independent provider and
human/finding/merge gates remain outstanding. Historical trial counts are unchanged.
