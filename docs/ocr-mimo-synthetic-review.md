# Synthetic diff review with OpenCodeReview + MiMo

[English](ocr-mimo-synthetic-review.md) | [日本語](ocr-mimo-synthetic-review.ja.md)

## Observed stage

The pinned Alibaba OpenCodeReview v1.13.7 CLI is now invoked with `review`, not `llm test`. Both bundled clean/defect synthetic source pairs are materialized in fresh temporary Git repositories. Only source files go into these repositories; the ground-truth manifest, mock review JSON, and the working project's files are not copied or sent. The actual generated Git diff SHA256 is recorded per sample.

Verified: real CLI + loopback mock review, four selected cases in one invocation (0.875s). Together with the previous five connection cases, this trial uses **9/10 case executions in two invocations**. No automatic CI was added and no new paid requests were made by this change.

Earlier connection evidence is distinct: an operator-reported bounded live connection receipt showed two completed MiMo responses and a tool round trip, not a code review. The agent did not receive or store the operator's API key. **Live synthetic review and quality acceptance remain pending.**

## Run

No additional Python dependencies. Use the same pinned binary as the [connection step](ocr-mimo-standalone.md).

```sh
# Default: real CLI + loopback mock. Receipt must not exist.
python3 tools/ocr_mimo_review.py --binary /absolute/path/to/pinned-ocr --receipt /private/non-git-directory/new-mock-review.json

# Paid review: use the same terminal where MIMO_API_KEY is already exported.
python3 tools/ocr_mimo_review.py --binary /absolute/path/to/pinned-ocr --live --receipt /private/non-git-directory/new-live-review.json
```

Run the live command once only after accepting the limits below. Do not rerun the connection probe. An interrupted receipt or FAILED_OR_UNKNOWN requires reconciliation, not a retry. The exclusive receipt has mode 0600; initial unknown status is fsynced before execution. Findings are retained only in that private receipt, not echoed to terminal or published.

The child CLI receives only an ephemeral loopback token, not the MiMo key. No HOME override or global configuration edits. Existing OCR configuration or a global rule file blocks execution pending reconciliation. Temporary repository Git configuration ignores caller/system configuration and disables hooks/signing for its synthetic baseline commit. Upstream may persist synthetic review sessions under the operator's normal OCR session store; the runner does not delete those records.

## Execution bounds (not a dollar cap)

- Fixed model `mimo-v2.6-pro`, endpoint `https://api.xiaomimimo.com/v1/chat/completions`.
- **8 HTTP attempts total shared by both samples**, including planner/tool rounds and failed/unknown requests.
- Per request: 65,536 body bytes, output parameter 2,048 tokens, HTTP timeout 30 seconds. CLI timeout 150 seconds per sample.
- Single worker, low effort, no post-filter call. Production transport never retries, redirects, or selects another model/endpoint.
- Any forwarding/validation failure latches closed and stops the remaining sample. A CLI zero exit alone is not success: completed same-model relay evidence, one reviewed file, complete/success JSON, no warnings, and valid finding locations are required.
- Input bytes are not exact input tokens. **No enforced dollar cap**; actual live cost remains unknown. At the public overseas cache-miss rates checked 2026-11-11 (input $0.435/M, output $0.87/M), cost depends on actual usage. These bounds differ from the earlier two-request connection probe.
- A complete review with zero findings is valid execution evidence, **not evidence of no defects**.

## Result handling and remaining work

Raw OCR categories such as `security` and `bug` are preserved. They are not converted to exact subcategories such as `security/path_traversal`. The existing mock-only scorer is unchanged; real outputs are never mislabeled mock to enter it. False positives, missed defects and fine-category matches are not automatically accepted; inspect findings against the separate ground truth locally. All outputs retain `review_quality_accepted=false`.

Next: operator-run bounded live synthetic review, then human adjudication of clean false positives and four seeded defects. Machine subtype scoring, explicit quality/cost acceptance, Mailbox integration, Cloudflare auditing and unattended rollout remain unfinished.

Selected checks:

```sh
python3 tests/check_ocr_mimo_review.py --binary /absolute/path/to/pinned-ocr
```

Do not repeat these four cases in the same trial without a budget increase: only one of ten case executions remains.
