# Changelog

[English](CHANGELOG.md) | [日本語](CHANGELOG.ja.md)

## 2026-11-08

- Simplified the bilingual README to the high-level role map, logical architecture and navigation.
- Updated the English/Japanese Mermaid topology sources and added a dated explanation based only on already-public project records. No new internal operating status, schedules, test results, account details or security settings are included.
- Added an archive index linking the complete prior overviews and diagram sources at an immutable commit. Existing dated documents and rendered historical diagrams remain in place; detailed past content is not duplicated into new snapshots.
- Documentation only: no runtime, permission, credential, schedule, sending-limit or deployment changes, and no new machine/model tests.

## 2026-11-02 (Asia/Tokyo)

- Brought the bilingual README's current architecture up to the 2026-11-02 state and updated the Mermaid diagram to match: Muse (Fuwatchi) recorded with its direction / design / review / media role; the home lab's Mac mini (M4, arrived 2026-11-01) with OpenClaw as gateway and the read-only-start lab-operations agent Kurocchi (LINE for daily contact, Discord for lab notifications); the OCI cloud development environment midorun running Claude Code, with Claude Code (CLI) decided as the development axis for both the cloud environment and the home lab; Antigravity restricted to the official client on the owner's own devices (not deployed to OCI or OpenClaw); Dots as the home-lab build and operations lead; Fuwatchi's lounge status share at every 2 hours since 2026-11-01.
- Updated the full-size network topology diagrams to the 2026-11-02 state ([EN PNG](assets/network-topology-2026-11-02.png) / [JA PNG](assets/network-topology-2026-11-02.ja.png); Mermaid sources in `tools/architecture/`): removed the Ghost in the Log app node (a single app, unrelated to the overall architecture; the Neon Postgres node went with it), made midorun (OCI) an explicit node in the topology, and added Kurocchi as the third resident agent — governing the home lab (Mac mini and Intel NUC) and maintaining and operating the applications on Vercel. The 2026-10-30 PNGs are kept in place as the older snapshot.
- **This repository change is documentation only; the decisions and environment changes above were made and executed outside it on 2026-11-01–02.**

## 2026-10-16 (Asia/Tokyo)

- Added the bilingual [Daybreak and authorized OSS security review](docs/daybreak-authorized-oss-security-review.md) page: Daybreak Blue/Red per OpenAI's public documentation, models listed in the API guide, naming discrepancies between sources (unresolved), and a proposed operating procedure for authorized OSS review.
- **Documentation only. Access is not held or claimed; no Daybreak request, scan, credential, model, permission or runtime change.** Routine model selection and the MiMo review default are unchanged.

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
