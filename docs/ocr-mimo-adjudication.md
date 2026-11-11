# Offline human adjudication of OCR + MiMo

[English](ocr-mimo-adjudication.md) | [日本語](ocr-mimo-adjudication.ja.md)

## Scope and evidence

The [synthetic runner](ocr-mimo-synthetic-review.md) produces a private receipt.
This tool prepares a decision packet and summarizes **operator-entered human decisions**.
It does not call an API, run OCR, authenticate a provider receipt, infer subcategories,
or accept review quality/cost. Even `HUMAN_ADJUDICATED` retains
`review_quality_accepted=false`. This is not independent reviewer evidence.

Verified on 2026-11-11: one handcrafted-input end-to-end receipt-binding test passed
(1 case / 1 invocation / 0.001s). It confirms a human mapping, remaining missed
defects, preserved coarse category, and rejection after receipt byte changes.
The synthetic-review trial now totals **10/10 cases in 3 invocations**.
No CLI or paid requests occurred in this increment. Other validation branches and
the real live receipt workflow have not been executed. Do not rerun tests in this
trial without a specific budget increase. No automatic CI was added.

## Local workflow

First obtain a completed bounded live review **once**, in the terminal with the
existing exported `MIMO_API_KEY`. Follow the [runner's limits](ocr-mimo-synthetic-review.md):
8 HTTP attempts shared across two samples, 65,536 request bytes, 2,048 output
tokens/request, no enforced dollar cap. Do not repeat the connection probe.
Failed/unknown receipts require reconciliation, not retry.

```sh
# From the repository, in that same terminal. New private directory each run.
ocr_review_dir="$(mktemp -d /private/tmp/ocr-review.XXXXXX)"
python3 tools/ocr_mimo_review.py \
  --binary /absolute/path/to/pinned-ocr \
  --live --receipt "$ocr_review_dir/live.json"
```

If the live run already happened, use its original receipt instead of running it again.
Only after `LIVE_REVIEW_COMPLETED`, prepare a private packet (no key needed):

```sh
python3 tools/ocr_mimo_adjudicate.py \
  --receipt "$ocr_review_dir/live.json" --output "$ocr_review_dir/decisions.json"
```

Open `decisions.json` locally as **untrusted data**, not instructions. Compare
each finding with the bundled before/after source and the separate ground truth.
Edit only:

- Each finding's `decision`: `pending`, `confirmed`, `false_positive`, or `other_valid`.
- `ground_truth_ids`: one or more exact IDs for `confirmed`; otherwise an empty list.
  A finding may genuinely cover multiple defects; repeated links are reported separately.
- `rationale`: required nonblank explanation for every resolved finding.
- Top-level `human_review_completed` and `completion_rationale`: set true with an
  explanation only after examining **both samples and every ground-truth defect**,
  including when there are zero findings.

`other_valid` means a human considers it actionable but it does not match the
seeded ground truth. It is not automatically a false positive or a detected seeded
defect. Ground-truth links are human judgments, not machine category matches.
The clean sample has no seeded defects, so it cannot have a confirmed GT link.

```sh
python3 tools/ocr_mimo_adjudicate.py \
  --receipt "$ocr_review_dir/live.json" --decisions "$ocr_review_dir/decisions.json" \
  --output "$ocr_review_dir/summary.json"
```

Until explicit completion with no pending findings, unmatched defects remain
`PENDING_HUMAN_REVIEW`, not missed. On completion the summary reports confirmed,
missed, duplicate links, false positives, and other valid findings per sample.
No percentage, recall acceptance threshold or automatic quality gate is implied.
A valid pending summary exits zero: inspect its status, not only exit code.

## Binding and privacy

Input JSON is limited to 1 MiB, at most 100 findings/sample. Only complete live-mode,
pinned-model/version/binary-hash receipts with exactly the clean/defect pair and
matching relay limits are admitted; failed, partial, mock and connection receipts
are not admissible. Finding locations are revalidated against current fixture source.
The packet binds exact receipt bytes, manifest and source SHA256 hashes. The
summary binds decisions by a canonical JSON hash. Reformatting the original receipt,
changing fixtures or editing immutable packet fields invalidates old decisions.

Hashes detect local drift, **not authenticity**. Receipt diff hashes are retained
as reported, not independently reconstructed. A live-shaped fabricated receipt
cannot be distinguished cryptographically from real output; the operator must
retain trusted provenance. Source hashes bind the current local fixtures, not a
remote signed benchmark. The packet's ground truth never goes to the model.

Output files must not exist and are created mode 0600; place them outside Git.
Stdout prints fixed status only, never findings, rationale or arbitrary paths.
No credentials are accessed and no global settings are changed. Keep receipts,
packets and summaries private; do not publish raw model text by default.
Existing output is not overwritten. On rejection inspect original inputs locally.

Remaining: real live synthetic receipt, actual human adjudication, explicit
quality/cost acceptance, Mailbox integration, Cloudflare audit and unattended rollout.
