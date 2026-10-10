# AI Team Work Allocation Update — 2026-10-10

[English](operating-decisions-2026-10-10.md) | [日本語](operating-decisions-2026-10-10.ja.md)

Allocate research, prose and GitHub documentation broadly to Claude / Antigravity. Keep Dottie focused on short PM work and Codex / ChatGPT on complex initial design, difficult decisions and final escalation when needed. Full-text substitution and comprehensive Codex re-review are not the default. This is owner-directed documentation policy, not implemented or verified autonomous dispatch.

## Responsibilities: production and research work

| Worker / environment | Candidate work | Boundary |
|---|---|---|
| Owner | Goals, priorities, accountable approval, final acceptance and publication decisions | Verify outputs and retain relevant specialists |
| Dottie | Short requirements, acceptance criteria, allocation, progress and handoff | Not the standing long-form author or autonomous dispatcher |
| Codex / ChatGPT (Chappy) | Complex initial design, difficult decisions and final escalation when needed | Do not routinely rewrite or comprehensively re-review every deliverable |
| Claude Code | Implementation, fixes, tests, technical docs, blog drafts/editing/translation, GitHub docs and PR preparation | Check availability, fit and fresh capacity; publication/production actions need appropriate authorization |
| Gemini / Antigravity | Research, official-source checks, comparison tables, summaries, chart data, PoCs/mocks, alternative prose and independent first review | Allocate with Claude using the same criteria; different tools may share a provider |
| Local Qwen (Windows / Mac) | Authorized specialist research and source organization, including permitted security/social topics where suitable | Verify model capabilities, search and source checks per environment; never bypass safety controls |
| RunPod A100 Qwen | Future independent-review candidate | Live operation and quality are not accepted; use Claude / Antigravity mutual review for now |

## Allocation and handoff failures

1. Record the goal, completion criteria, small input, worker, one alternative, planned budget/work limit, and artifact/evidence for each task.
2. Confirm the authorized route is available and actually working. Separate subscription/API and provider pools, timestamped session/weekly capacity, and reset times. Missing/stale values are `unknown`. Do not add unlike provider token units to equalize work.
3. First allocate to a fitting Claude / Antigravity candidate with available capacity. The role table is not a fixed assignment. Manual rotation when observations are stale is a proposal to reduce concentration, not proof of sufficient capacity.
4. After one failed handoff, preserve the cause and artifacts. Stop on authorization denial; do not bypass it through another route. For ordinary availability failures, consider one other authorized candidate. If none works, mark `blocked` / awaiting owner handoff; do not automatically return to full-text Codex substitution. Record a short reason for exceptions.
5. Separate builder/author and reviewer by provider where possible. Claude inside Antigravity and native Claude Code have separate pools but share a provider. Review the specified scope, evidence and major unknowns; escalate only difficult points to Codex when needed.

Quota observation is manual; live quota retrieval and autonomous dispatch are unverified. Do not claim automatic CodexBar image reading. Respect authorization and safety controls; role changes must not bypass denial. Windows remains first choice; consult the owner before switching to Mac if unavailable.

## Routing examples

| Work | Allocation example | Evidence and acceptance |
|---|---|---|
| Research, blogs and docs | Antigravity research/official sources → Claude draft/edit/translation → Antigravity chart data → different-provider review → owner approval → authorized publisher | Source URLs/dates, draft revision, numeric data, findings/fixes. Four-channel blog drafts remain unpublished before owner review |
| Code, fixes and tests | Short Dottie specification → Codex initial design if needed → Claude or Antigravity implementation/tests → different-provider review → worker fixes/rechecks → owner acceptance | Diff, checks and unverified runtime; review does not become a complete reimplementation |
| General repo edits and PR preparation | Small input + edit scope → Claude docs/PR preparation (alternative Antigravity) → another worker checks diff/links → authorized upload | Branch, changed files, preserved existing changes and readback. Merge only within separately explicit authorization |
| Authorized specialist research | Local Qwen organizes sources → search-capable worker checks official sources → scoped Claude / Antigravity review → owner decision | Environment/model observations, permitted scope, sources/unknowns; no role change to bypass safety features |

These examples are candidate assignments, not claims of completed execution. Bound inputs and acceptance criteria; hand off only necessary artifacts/evidence. Creation, review, owner approval, publication and merge are separate stages.

## Two Qwen tracks and evidence limits

- **Local:** Windows Open WebUI/Ollama text responses were owner-checked. Mac Open WebUI 0.11.4 with Qwen2.5 3B has past observations of local responses and web-search results. Search availability and specialist-research quality require environment-specific checks; this is not automated orchestration.
- **RunPod Phase 1:** [PR #39](https://github.com/moruku36/qwen-multimodal/pull/39) records one real response from small Qwen2.5-1.5B-Instruct and Pod deletion. It does not accept A100 independent-review quality or the complete workflow.
- **RunPod Phase 2:** Mock/offline only. Live A100 independent review, quality and ongoing operation are not accepted. Use Claude / Antigravity mutual review for now. The conversational label “around 3.7” is unresolved and is not a model ID.
- **Colab:** The fixed-Q8 chat notebook is separate. [PR #35](https://github.com/moruku36/qwen-multimodal-colab/pull/35) reports 287 CPU CI checks (2 skipped), not Colab/GPU inference, model-download or A100-quality verification.
- OpenAI-compatible describes an API shape, not paid OpenAI. A single HTTP response does not establish automatic startup, connection and termination. Pod stop and deletion differ, including storage costs and data retention. This documentation change starts no GPU and changes no runtime settings.

## Retained policy and public boundaries

- Preserve the [2026-10-06](operating-decisions-2026-10-06.md) OpenAI Medium choices and model-label caveats. This document limits when work returns to OpenAI; record exception reasons. Do not infer model IDs or runtime identity.
- Factory is the thin handoff/artifact/evidence layer; AIteamBridge is separate local engineering. Neither establishes live automatic allocation.
- Do not publish private conversations, personal/family details, credentials, login destinations, account/quota details or identifiers. New charges, authentication and settings changes are out of scope.
- Retain the [Oct 2](operating-decisions-2026-10-02.md), [Oct 5](operating-decisions-2026-10-05.md) and [Oct 6](operating-decisions-2026-10-06.md) records without retroactively changing their observations or historical policy.

The [routing guide](routing-guide.md), [AI team](ai-team.md) and [handoff templates](handoff-templates.md) follow this policy.
