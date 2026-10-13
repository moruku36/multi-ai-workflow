# PR Review Pipeline Operating Update — 2026-10-13

[English](operating-decisions-2026-10-13.md) | [日本語](operating-decisions-2026-10-13.ja.md)

Updated: 2026-10-13 (Asia/Tokyo). Retain the [2026-10-10 allocation policy](operating-decisions-2026-10-10.md), with the following extension specifically for code PR review. Historical observations and records remain unchanged.

- **Codex Review:** bounded independent review for Claude/Gemini implementations. Claude/Gemini review Codex implementations; distinguish this from same-provider self-review.
- **PR Review Pipeline:** freeze PR head → separate AI review and CI → validate findings and apply minimal fixes → recheck the new head → merge by risk and authorization.
- **Evidence and acceptance:** record reviewer/provider, SHA, tests, findings and gaps. Unknown or incomplete states cannot pass.
- **Risk tiers:** low-risk auto-merge remains a future conditional proposal; medium/high risk requires human acceptance. Automation, required checks and protections need separate configuration and verification.
- **Qwen:** RunPod A100 review remains an unaccepted future candidate. This update implies no GPU startup, model selection or quality acceptance.
- **Documentation alignment:** update English/Japanese README, roles, routing, handoffs, repository maintenance, changelog, review rules and PR template.

See the [detailed design](pr-review-pipeline.md) and [changelog](../CHANGELOG.md). Verification covers documentation and templates, not completed live Codex Review, enforced CI, cross-provider evaluation or auto-merge operation.
