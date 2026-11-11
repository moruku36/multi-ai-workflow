# OpenCodeReview + MiMo: first standalone connection step

[English](ocr-mimo-standalone.md) | [日本語](ocr-mimo-standalone.ja.md)

## Update, 2026-11-11

A subsequent operator-reported live connection receipt confirmed two MiMo responses and a tool round trip. This is not review quality acceptance. The next [synthetic diff review step](ocr-mimo-synthetic-review.md) adds the actual CLI review entry point, locally mock-verified; live diff review remains pending. The sections below preserve the original implementation-time snapshot.

## Historical status, 2026-11-11

**Implemented: a pinned real-CLI connection probe and a local mock tool-call round trip. Live MiMo connectivity is NOT verified.** This is not completed code review, quality evaluation, Mailbox integration, or Cloudflare audit integration.

This prepares the standalone P3 path in the [roadmap](mailbox-quality-roadmap-2026-10-26.md). The existing `eval_ocr_mimo.py` remains mock-only and has not been changed.

## Pinned dependency

- [Alibaba OpenCodeReview v1.13.7](https://github.com/alibaba/open-code-review/releases/tag/v1.13.7), source commit `b1dcffb0729f3f2e3e47170968a5014a2e035580`.
- Apache-2.0, used as an external official CLI; no vendoring or upstream modifications.
- Official release SHA256 digests for each platform are pinned in `tools/ocr_mimo_connection.py`. Unknown binaries are rejected before execution.
- Only Darwin arm64 was downloaded and exercised in this change. Other platforms are not execution-verified.

Example download in an existing work directory outside the repository:

```sh
curl --fail --location --proto '=https' --tlsv1.2 --output ./opencodereview-v1.13.7-darwin-arm64 https://github.com/alibaba/open-code-review/releases/download/v1.13.7/opencodereview-darwin-arm64
shasum -a 256 ./opencodereview-v1.13.7-darwin-arm64
chmod u+x ./opencodereview-v1.13.7-darwin-arm64
```

Expected SHA256: `ce2eab495483f9b119992b48253a4e2f6969c27c3b02514350d9e7aa0083b4e8`. Stop without execution on a mismatch.

## Usage

No third-party Python packages are needed. An existing `~/.opencodereview/config.json` blocks the probe: upstream gives it priority over environment variables, and it could select another provider, execute a key command, or enable telemetry. The probe does not delete/overwrite that configuration or repurpose HOME.

```sh
# Preflight only: no network or CLI execution.
python3 tools/ocr_mimo_connection.py --binary /absolute/path/to/pinned-ocr

# Real CLI, synthetic loopback replies only, no external transmission.
python3 tools/ocr_mimo_connection.py --binary /absolute/path/to/pinned-ocr --mock
```

The pinned CLI runs `llm test`: its embedded synthetic conversation, one `ocr_selftest` tool call, a fixed tool result, then a final answer. No repository code or ground truth is input. A mock success is `MOCK_PASSED`, never `CONNECTED`.

## Live MiMo connection: not executed

Use only after authorized secret injection makes an existing `MIMO_API_KEY` available and model availability, pricing, and the trial spending conditions are confirmed. An OpenClaw model registration is not an environment credential for an external CLI. No automatic secret discovery/copying is implemented. Never put the key in arguments, source, public logs, or Git.

```sh
python3 tools/ocr_mimo_connection.py --binary /absolute/path/to/pinned-ocr --live --receipt /private/non-git-directory/new-probe-receipt.json
```

- Fixed endpoint: `https://api.xiaomimimo.com/v1/chat/completions`; fixed requested model: `mimo-v2.6-pro`.
- Upstream's suggested model list includes older names. Availability and the returned identity of the requested newer model remain unverified. No automatic alternative model or route.
- Only the parent relay holds the real key. The CLI receives an ephemeral loopback token.
- At most **two upstream HTTP attempts total**, including failed or unknown attempts. The relay never retries and latches closed after errors.
- Per request: at most 8,192 body bytes, an output limit parameter of 1,024 tokens, and a 30-second HTTP timeout. Overall CLI timeout: 70 seconds.
- The byte ceiling is NOT an exact input-token ceiling. **A dollar spending cap is not implemented**, and this probe does not guarantee the roadmap's proposed $0.10. Do not start live execution until pricing and spending-bound treatment are settled.
- Success requires CLI exit 0 AND two completed same-model responses, the self-test tool result in the second request, and a completed final response.
- A receipt is exclusively created with mode 0600. Reusing a path is rejected. Reconcile interrupted receipts or `FAILED_OR_UNKNOWN` results instead of automatically rerunning.
- Missing usage and live cost remain `unknown`. Model content and CLI stdout/stderr are neither retained nor displayed.
- The relay binds only to loopback for the command's lifetime and closes afterward. No daemon, schedule, or global configuration change.

## Verification and remaining work

One selected invocation: **5 tests passed in 1.726 seconds**, using 5 of the maximum 10 case executions for this development trial. Covers the pinned real CLI/mock round trip, environment and auth separation, unknown-outcome stopping, byte/model boundaries, the two-attempt cap, and rejecting exit 0 without evidence. Live API calls: zero.

```sh
python3 tests/check_ocr_mimo_connection.py --binary /absolute/path/to/pinned-ocr
```

After live authentication/model/pricing verification, perform a bounded connection trial; only then move to real OCR review of clean and defect-seeded public synthetic diffs. A diff-review execution entry point, live-result ingestion/scoring, quality/cost acceptance, Mailbox integration, and Cloudflare high-risk routing remain unimplemented. No automatic CI or repository-wide rollout was added.
