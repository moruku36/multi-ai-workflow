# Observed response reason

[日本語](review-response-reason.ja.md)

2026-11-12: diagnostic draft; three cases **UNEXECUTED**.
Local isolated execution stopped during memory-limit setup, before any test ran.
The three-case, one-invocation allowance is approved but unused. No live recovery claim.
PR54 receipt: Alibaba `cli_exit_nonzero`, HTTP 2, completed 1;
Cloudflare `response_validation`, HTTP 1, completed 0, completion tokens 2048.
Cause **UNKNOWN**; token count alone does not establish truncation.

Optional `response_reason` records only `length_stop` (explicit length finish),
`model_mismatch`, `malformed_response` (JSON/envelope), or `unexpected_tools`
(Cloudflare). Unknown values are omitted. No raw response, errors or credentials.
Bounded non-throwing observation precedes Alibaba inherited validation and runs
at Cloudflare validation; validators and central hub are unchanged.
Receipt boundaries reproject through `safe_diagnostics`.
Old receipts/reservations, caps, attempts, deadlines, provider/model, source limits,
no-retry and trust/activation/merge gates remain unchanged.

Three mocked cases: Cloudflare length stays incomplete after one attempt;
Alibaba malformed response stays rejected while retaining its reason;
receipt/central projection rejects arbitrary strings and retains an observed code.
No test body, build, network or provider ran. No same-head review acceptance.
Requires supported isolated execution, not another generic approval:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tests/check_review_response_reason.py
```

Offline success would not prove live recovery. Never replay reserved pairs.
