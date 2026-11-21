# Sidekick advisory transport witness

[English](sidekick-advisory-transport.md) | [日本語](sidekick-advisory-transport.ja.md)

This candidate covers one neutral check on public `moruku36/local-ai-sidekick` PR 26 at the base and head pinned in the entrypoint. The check records provider-free transport only. It carries no review, acceptance, or merge authority. Signed dual review and human disposition have their own gates. [Workflow](../.github/workflows/sidekick-advisory-transport.yml) · [Entrypoint](../tools/sidekick_advisory_transport.py)

The owner can dispatch the workflow on its first attempt once the approved workflow revision is on the Hub's default `main`. Set `confirmation` to `WRITE ONE NEUTRAL SIDEKICK PR 26 ADVISORY CHECK` exactly. The workflow uses the existing App configuration and requests a token for Sidekick with pull requests read and checks write. The installation scope, PR identity, pinned commits, and current `main` tip must match before the check is submitted.

The script scans all visible check runs on the pinned head across Apps and statuses. An existing matching name or stable external ID stops the dispatch. It also reads classic protection and active rules for `main` through public REST. A collision with a required context, unreadable protection, or an incomplete check scan stops the dispatch before the POST. Keep `central-hub-advisory-transport-v1` out of required checks. The preflight reads and check creation are separate GitHub operations, so they cannot exclude a concurrent PR or protection change between the last reads and the POST.

After the single POST, the script reads the check by ID and verifies the App, head, context, external ID, and neutral conclusion. If execution stops after submission without a verified readback, reconcile using read-only GitHub records for the pinned head and the stable external ID in the entrypoint. Treat a lost response, timeout, or failed readback as unresolved even if the check is initially absent. Do not rerun or issue a fresh dispatch to replay that write.

The entrypoint passed five fake-HTTPS tests. Its read-only checks also passed against the public Sidekick PR, runs, branch, and effective rules on November 21, 2026. Neither result establishes installed-token scope or live check delivery. [Offline tests](../tests/test_sidekick_advisory_transport.py)
