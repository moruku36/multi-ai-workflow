[日本語](cache-engineering-future-study.ja.md) | **English**

# Future study: Agent KV cache control

**Status: proposal, not implemented.** This document does not claim that the current workflow uses AKV, has achieved a cost saving, or can perform KV operations through any provider API.

[Cache Engineering for Agents (arXiv:2610.28577v1)](https://arxiv.org/html/2610.28577v1) proposes `drop` and `repos` operations over KV state without editing the text trajectory. The companion survey in the research repository records the authors' evidence and its limits. We have not checked the author code or ported it here.

This could apply to long tool-using trajectories on a serving backend under our control. Provider prompt caching, text summarization, and direct KV operations are separate mechanisms. The cache-hit hypothesis in the existing [MiMo efficiency review](reports/2026-10-19-mimo-efficiency-review.md) also needs separate measurement.

## Proposed sequence

1. Record backend capability and API behavior. Keep the current approach if direct KV operations are unsupported. API compatibility does not imply that arbitrary provider APIs accept these operations.
2. Keep text trajectories and cache-operation logs separate. Isolate cache state by model, tenant and operation history; do not assume it can be shared across agents.
3. Compare full history, summarization and rolling-drop using the same tasks, budget and stop conditions. Measure success, actual bills or GPU time, KV memory, P95 latency and correctness after restoration.
4. Require quality non-inferiority as well as savings. Include old constraints, branching, retries and process restart in regression checks.

A free first step is to inspect public trajectories and use a simulated state machine to detect collisions between identical token sequences with different operation histories. This would not reproduce GPU performance. Implementation and adoption remain pending.

[README](../README.md) | [MiMo efficiency review](reports/2026-10-19-mimo-efficiency-review.md)
