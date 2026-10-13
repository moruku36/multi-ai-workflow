# Changelog

[English](CHANGELOG.md) | [日本語](CHANGELOG.ja.md)

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
