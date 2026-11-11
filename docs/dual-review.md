# Alibaba + Cloudflare review integration

[English](dual-review.md) | [日本語](dual-review.ja.md)

## Implemented, not running automatically

Cloudflare's [security-audit-skill](https://github.com/cloudflare/security-audit-skill)
is vendored unchanged in [.agents/skills/security-audit](../.agents/skills/security-audit/SKILL.md)
at commit `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8`.
The [MIT license](../third_party/cloudflare-security-audit/LICENSE),
upstream README and SHA256 manifest are retained. The installer verifies Git blob
hashes before writing, uses no package manager or install hooks, and never runs
upstream code. Executable upstream scripts are stored as ordinary files; invoke
their documented Node commands only when the relevant audit is authorized.
This is a repository-local installation, not a global OpenClaw skill registration
or a claim that every client discovers this directory automatically.

`tools/dual_review.py` prepares a private same-revision handoff and checks recorded
lane status. It does **not** invoke either reviewer, configure credentials, install
a Git hook, enable Actions, publish a comment, or authorize a merge.

## Per-change contract

For code changes in this repository, the intended workflow is:

1. Finish a feature commit with a clean worktree.
2. Prepare one handoff with immutable base/head SHAs.
3. Run Alibaba OpenCodeReview + MiMo on that range.
4. Have an eligible coding agent perform a focused Cloudflare-guided source review
   on the same range. Read SKILL.md and relevant companions explicitly if the
   client does not discover the repository skill.
5. Record both actual reviewer identities, providers/models, execution evidence,
   findings and unresolved issues. Recheck current head and worktree.
6. Resolve findings, obtain required independent-provider review and human
   acceptance. Any new commit invalidates the old handoff.

A focused diff review uses the upstream **guidance mode** and is partial coverage.
It is not the full six-phase audit, a penetration test or a Cloudflare service.
A full audit requires explicit scope, independent agents, validators, appropriate
budget and sandbox controls. Do not execute target code without those controls.
Cloudflare is a tool/methodology publisher, not the actual model provider.
Two tool names do not establish reviewer independence.

## Prepare and inspect

Use full 40-character commit SHAs and an existing private parent directory.
The output must be a new directory outside the target repository:

```sh
python3 tools/dual_review.py prepare \
  --repo /absolute/path/to/repository \
  --base FULL_BASE_COMMIT_SHA --head FULL_HEAD_COMMIT_SHA \
  --output /absolute/private/parent/new-dual-review
python3 tools/dual_review.py status --run /absolute/private/parent/new-dual-review
```

Preparation is local and key-free. It requires a clean worktree (including
untracked files), checks the vendored hashes, and bounds the diff to 65,536 bytes.
It writes private `plan.json`, `change.diff`, `REQUEST.md` and
`receipt-template.json`. The latter is a shape template, **not execution evidence**.
The request carries the lane-specific limitations. No repository content executes.

After actual review, the coordinator writes separate `alibaba.json` and
`cloudflare.json` receipts in that directory using the template shape.
Never fill pending receipts with fabricated completions.
Status rejects missing, malformed, pending and stale bindings.
`BOTH_RECORDED_NOT_ACCEPTED` means both reviews were **recorded**, including
possibly unresolved serious findings. It is never approval. Receipts are operator
assertions; hashes check consistency, not authenticity. Do not consume this as a
required merge check or a trusted CI attestation.

## Verification and remaining work

The preceding OCR development trial remains **10/10 cases, 3 invocations**.
No additional cases, upstream validator tests or live API calls were executed
for this increment. Three selected receipt-gate cases are authored in
`tests/check_dual_review.py` but unexecuted; request an explicit three-case budget
increase before running them. Preparation filesystem/Git paths are also untested.

The existing `ocr_mimo_review.py` handles bundled synthetic samples **only**.
Its prior live result is not review evidence for a normal feature branch.
Still required before automatic per-PR operation:

- bounded real-diff Alibaba adapter reusing the parent-only MiMo relay;
- an actual eligible coding-agent invocation route for the Cloudflare lane,
  with observed provider/model and separate-reviewer evidence;
- selected verification and one bounded dual-lane acceptance run;
- credential injection and explicit recurring-call/spending limits;
- event trigger, deduplication by head, timeout/unknown-result reconciliation,
  and private artifact handling.

No recurring API spend, schedule, global configuration or repository protection
was enabled. Existing synthetic quality acceptance remains pending.
