# Optional static checks in the quality wrapper

[English](quality-wrapper-integration-2026-11-05.md) | [日本語](quality-wrapper-integration-2026-11-05.ja.md)

## Offline integration delivered

The existing `tools/check_quality.py` now accepts explicit `--static-target` inputs and optional `--static-tool` selection. With no new flags, it executes no static engines and retains the baseline pass/fail behavior. A baseline pass does not claim Ruff or Semgrep completed.

When selected, the already tested standalone adapter runs once. Its report, source hashes, findings, statuses, and limits are included under `results.selected_static_checks`. Findings, missing tools, incomplete output, timeouts, exceptions, and malformed/empty success reports fail the overall result. A static pass cannot hide an existing baseline failure. Ruff formatting, unselected engines, and files outside the selected scope remain explicitly unverified.

```sh
python tools/check_quality.py --json --static-target tools/run_static_checks.py --static-tool ruff --static-tool semgrep
```

Targets are relative to the wrapper's repository. The standalone adapter remains the entrypoint for a different pilot repository. No daemon, CI, cross-repository deployment, authentication, or settings change is included. The historical baseline uses `py_compile` and can write `__pycache__`; the static adapter itself still scans temporary source copies without fixes.

## Reuse procedure

1. Use a full, authorized checkout and verify its current head. The verification base is `8a0877ab5225cbb806389e1a19842bbce71a47e3`; GitHub main was checked again and matched during publication preparation.
2. Check whether these changes are already present and apply them only to an unmodified checkout. When using a patch, run `git apply --check` first; reconcile conflicts instead of overwriting newer work.
3. Use already approved Ruff 0.17.3 / Semgrep CE 1.183.0 from an executable path outside the target repository. Their earlier two-file synthetic acceptance scope is recorded in the standalone adapter documentation. Do not infer they are installed in a fresh environment.
4. Run the command above once in the full checkout. Retain the JSON and exact head. Required baseline suites missing from a partial snapshot must remain a failure, not be disabled for a green report.
5. Review actual findings and decide the pilot repository scope. Keep Alibaba OCR integration, Direct MiMo recovery, Cloudflare focused audit, and P2/P4 communication acceptance separate from this P1 gate.

## Initial offline verification, 2026-11-05

The initial offline work verified the input artifacts against their archive and file SHA256 hashes. Existing baseline tests plus new bridge tests passed offline. The tests simulate baseline checks and engine results where appropriate; the missing-engine path uses the real adapter without launching engines. No full repository gate or new engine scan was run. The previous installed virtual environment was absent, and no packages were reinstalled or external files written in this continuation.

At this initial stage the integration patches and test logs were local candidates. Subsequent complete-checkout and real-engine checks are recorded below.

## Initial full-checkout application attempt, 2026-11-06

The combined 12-file candidate was applied successfully to a clean complete checkout at `8a0877ab5225cbb806389e1a19842bbce71a47e3`, on the local branch `feature/quality-static-integration-20261106`. This identifies the inspected checkout, not a claim that the remote head was refreshed. At this initial stage, changes were uncommitted and unpublished.

- All 39 root regression tests passed (19 baseline, 12 adapter, eight integration).
- The aggregate baseline gate ran against the complete checkout: Python syntax passed for 26 files, fixture integrity passed for two samples, and documentation formatting passed for 58 Markdown files.
- The three required suites ran 88 tests with no skips. Three tests failed in the 54-test database-helper suite; the 27-test confirmed-memory and seven-test context-guard suites passed. That initial aggregate gate correctly returned **FAILED**.
- The local temporary-directory root itself has a `.git` marker. Synthetic database backup destinations therefore trigger the existing “outside any Git working tree” restriction. That restriction, the tests, and the system settings were not changed to force a pass. A single approved retry selected `/dev/shm` as the process-local temporary directory, verified outside any Git tree. All 88 required tests then passed with no skips, and the aggregate baseline gate returned **PASSED**. The initial failure log is retained. No safety check, test code, or persistent setting was changed.
- At this initial stage Ruff and Semgrep were unavailable in the command PATH. An actual adapter availability attempt returned `UNAVAILABLE` for both and exited 1, without launching either engine. An older Ruff 0.16.9 exists in an unrelated environment; it was not substituted for the accepted pinned 0.17.3 version. No packages were installed.

This verifies patch application and the complete-checkout baseline gate, but not real-engine acceptance. No Windows interaction, API call, push, deployment, credential change, or persistent runtime configuration change occurred in this continuation. Preserve the failed gate as evidence; do not present baseline acceptance or the 39 passing regression tests as acceptance of Ruff/Semgrep scanning.

## Pinned-engine acceptance and diagnostic fixes, 2026-11-06

A later authorized continuation installed Ruff **0.17.3** and Semgrep CE **1.183.0** into a temporary environment outside the repository. The official `https://pypi.org/simple` index was selected explicitly; all 67 wheels matched the previously accepted SHA256 lock. No source builds, unpinned substitution, authentication, or repository upload was used. The installed package metadata and official wheel URLs/hashes are recorded separately; the adapter's Ruff JSON version remains `unknown` by design.

The real wrapper invocation explicitly selected only `tools/check_quality.py` and `tools/run_static_checks.py`. Ruff passed. Semgrep initially found two pre-existing `except Exception: pass` handlers in document reading and executable discovery. They were fixed without suppressing rules: document-read failures now report the relative filename and exception type, and tool-discovery failures report `ERROR` plus the exception type rather than being indistinguishable from a missing executable. Raw exception messages are not reported. Empty successful discovery output is not marked available. Document-format checks remain advisory at the aggregate baseline level, as before.

Four focused regression tests were added. All 31 affected quality tests passed (19 baseline, eight bridge, four diagnostics); the unchanged adapter's 12 tests had already passed. The final end-to-end run then passed all 88 required tests and both real engines, with **zero findings on the two selected files**. Selected source hashes matched after scanning. The initial findings report is retained alongside the final pass; the only repeat engine run verified the code fixes. Engine limits, pinned rules, metrics-off settings, credential filtering, and failure semantics were unchanged.

The final command was:

```sh
TMPDIR=/dev/shm PATH="/absolute/path/to/approved/venv/bin:$PATH" python tools/check_quality.py --json --static-target tools/check_quality.py --static-target tools/run_static_checks.py --static-tool ruff --static-tool semgrep
```

This is acceptance of the existing baseline plus the selected two-file static scope, not a whole-repository security audit, Ruff formatting check, pilot-repository rollout, or live LLM evaluation. No push, deployment, Windows interaction, credential change, or persistent system/network configuration change occurred. This validation used the local diff before publication. Refer to the associated PR for current publication and review status. Temporary environment availability must be rechecked before later runs.

The check summaries and target hashes are in the [public validation record](quality-static-validation-2026-11-06.json). This is execution evidence from the builder, not an independent-provider review.
