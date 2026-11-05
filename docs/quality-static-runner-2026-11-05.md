# Local static-check adapter, 2026-11-05

[English](quality-static-runner-2026-11-05.md) | [日本語](quality-static-runner-2026-11-05.ja.md)

## Delivered scope

`tools/run_static_checks.py` is a standalone, standard-library adapter that executes **already installed** Ruff and Semgrep Community Edition against explicitly selected Python files. It does not install tools, modify sources, invoke an LLM, authenticate, push, or fetch remote rules.

The initial standalone delivery left `tools/check_quality.py` unchanged. A later offline continuation added an opt-in bridge, documented in [quality-wrapper-integration-2026-11-05.md](quality-wrapper-integration-2026-11-05.md). Its default behavior still executes no static engines. The Direct MiMo recovery remains separate, and neither delivery completes the entire P1/P3/P4 workflow. No daemon or CI was enabled.

## Usage

Run only with trusted, already approved binaries on an absolute PATH outside the target repository:

```sh
python tools/run_static_checks.py --repo-root /path/to/pilot --target app/main.py --tool ruff
python tools/run_static_checks.py --repo-root /path/to/pilot --target app/main.py --target app/service.py
```

Omitting `--tool` runs Ruff and then Semgrep sequentially. Repeat `--target` for each relative `.py` file. No directory expansion or whole-repository scan occurs. Repository-local executable shims and virtual environments are not auto-selected in this first version. POSIX is supported; Windows fails closed as `UNSUPPORTED_PLATFORM`.

## Checks and boundaries

- Ruff: `check`, Python 3.11 target, isolated configuration, no cache or fixes, minimal correctness selection `E9,F63,F7,F82`. Formatting is not checked. Inline `noqa` suppression is disabled.
- Semgrep: `scan --oss-only`, one job, local hash-pinned JSON rules, metrics/version checks disabled, strict errors, no Git-ignore influence, and inline `nosem` suppression disabled. The three initial rules flag dynamic `eval`/`exec`, selected `subprocess` calls with `shell=True`, and swallowed bare/`Exception` handlers. These are review candidates, not proof of exploitable vulnerabilities or complete security coverage.
- Only explicit ordinary UTF-8 Python files are staged. Symlinks, traversal, duplicates, nonregular files, and NUL bytes are rejected. Descriptor-relative bounded reads protect against symlink/FIFO replacement during selection.
- Limits: 50 files, 1 MiB per file, 5 MiB total, 30 seconds per engine, 2 MiB combined captured output, 1,000 findings. Semgrep additionally receives a 10-second rule timeout and 512 MiB memory setting. No retry or parallel engine execution.
- Each engine runs against a temporary copy with a temporary HOME/config/cache. Credential, proxy, and Python-hook environment variables are not inherited. Timeout and normal leader exit both trigger process-group cleanup. Uncertain cleanup stops the next engine.
- The flags and isolated configuration avoid intended network operations, but **are not an OS-level egress sandbox**. No claim of network containment is made. Use an approved offline runtime if a hard egress guarantee is required; this adapter does not change system/network settings.

## Result contract

The command emits JSON and exits 0 only if every requested engine completed cleanly. Missing engines, incomplete scans, malformed output, tool errors, timeouts, findings, and unsupported platforms return a nonzero exit.

The report contains source-content hashes, selected relative paths, normalized findings, and the bundled-rule hash. Semgrep must report every selected file in `paths.scanned` with `errors=[]`; zero or partial scans do not pass. Ruff's JSON has no scanned-path list, so its coverage claim is limited to the explicit validated inputs and successful check command. Raw source snippets, tool-provided messages, absolute diagnostic paths, and stderr are not copied into the report. Stderr is represented only by a hash. Ruff's version is `unknown` in this report; Semgrep's version is retained only when its output provides one. Record installed package versions alongside each acceptance run. The versions tested below are pinned in `tools/quality/requirements-static.txt`.

Statuses include `PASSED`, `FINDINGS`, `UNAVAILABLE`, `TOOL_ERROR`, `INVALID_OUTPUT`, `CONFIG_ERROR`, `TIMEOUT`, `OUTPUT_LIMIT`, `CLEANUP_ERROR`, and `NOT_RUN`. An absent engine is never a clean scan.

## Verification and remaining acceptance

Initially on 2026-11-05, neither engine was installed. Twelve focused tests passed: simulated clean/findings/error envelopes, partial/invalid Semgrep scans, limits, path/environment boundaries, pinned rules, and real local Python subprocess success/timeout/output-bound/descendant cleanup. Those subprocess tests exercise the adapter, not Ruff or Semgrep accuracy.

Later the same day, authorized official PyPI wheel installation in an isolated environment succeeded: **Ruff 0.17.3 and Semgrep CE 1.183.0**. One combined scan of `tests/fixtures/static_checks/clean.py` and `defect.py` was executed per engine. Both reported zero findings on the clean file. Ruff found the seeded undefined name (F821); Semgrep accepted all three bundled rules and found shell=True, eval, and the swallowed exception. Input hashes were unchanged. The wrapper correctly returned exit 1 for intentional findings; a separate fixture acceptance check passed. Installed versions and wheel-source hashes were recorded. No LLM/API call, authentication, push, or network-setting change occurred.

The later wrapper bridge consumes this JSON only when explicit targets are provided. Its offline verification includes the existing 19 baseline tests and eight integration tests; these are not new real-engine scans. Full-checkout acceptance and evaluation of the intended pilot repository remain. The two-file engine fixture verifies basic CLI/rule compatibility and seeded detection only, not general detector quality or complete security coverage. Keep live LLM acceptance separate. Existing MiMo trial/budget limits are unchanged and this adapter never calls MiMo.

The historic baseline is `8a0877ab5225cbb806389e1a19842bbce71a47e3`; the current-main `check_quality.py` blob was separately observed unchanged on 2026-11-05 (`d1b54668c947231543be6b2be5238121aa70625e`). This is not a full current-head repository test.
