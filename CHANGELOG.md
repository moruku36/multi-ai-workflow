# Changelog

[English](CHANGELOG.md) | [日本語](CHANGELOG.ja.md)

## v2026.10.15-r2 — 2026-10-15 (Asia/Tokyo)

- Adopted MiMo-V2.6-Pro API as the **planned** review default for code, validation and documents; Flash remains an optional pilot.
- Reassigned RunPod to GPU/model-serving experiments only, superseding the proposed recurring RunPod/Qwen review route.
- Require independent checks for serious findings, privacy assessment and measured quality/cost before rollout. Documentation only, no runtime or paid changes.

## 2026-10-15 (Asia/Tokyo)

- Added the [dated operating decision](docs/operating-decisions-2026-10-15.md): one bounded, final escalation to Claude Opus 5.5 Medium when a hard problem stalls under owner-selected GPT/Sol. It is owner operating judgment, not a claim that Opus is objectively best or always better than Sol.
- Added escalation rules to the bilingual README, roles, routing guide and a handoff template (evidence preservation, capacity/cost check, requested vs observed model, approvals, current-revision review, return to the ordinary model).
- Qualified the 2026-10-13 snapshot claims "Phase 2 mock/offline only" and "Codex as final escalation" as dated; older records are preserved.
- RunPod Phase 2 connection pass with Opus is an **owner report**; independent logs, Pod termination and billing stop are unconfirmed. A100 review quality and automated operation remain unaccepted. Mattermost is only a hard-problem example.
- **Documentation only; no GPU, model, TLS, permission or runtime change.**

## 2026-10-14 (Asia/Tokyo)

- Documented conditional Gemini 4 Argon integration, promoting Gemini from PoC/mock-only use to a candidate for routine code, tests and fixes **after verified Antigravity access and measured pilots**.
- Preserved Claude complex implementation, GPT-6/Codex architecture and bounded PR review, Dottie coordination, Qwen specialist research and unaccepted future review status.
- Updated bilingual README and routing; added bilingual [rollout architecture](docs/gemini-4-argon-rollout.md). **Documentation only; no runtime/model configuration changed.**

## 2026-10-13 (Asia/Tokyo)

### Added

- Codex Review / PR Review Pipeline design, architecture, reviewer separation, reproducible quality gates, repair loop and risk-based merge policy.
- PR review evidence handoff, bilingual PR template and repository-specific Codex review rules.
- Dated operating-decision record.

### Updated

- English/Japanese README, team roles, routing guide, handoffs and repository maintenance guidance to integrate the review procedure.
- Codex gains bounded PR review; Codex-authored work uses another provider. Preserve Qwen's unaccepted status and the two routine OpenAI Medium choices.

### Status

Documentation and templates only. No live configuration or verification of automatic review, scanners, required CI, repository protections or auto-merge. Previous operating-decision records remain historical.

[Design and architecture](docs/pr-review-pipeline.md) | [Operating record](docs/operating-decisions-2026-10-13.md)
