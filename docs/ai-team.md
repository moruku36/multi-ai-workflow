# AI Team: Names, Roles, and Operating Model

[English](ai-team.md) | [日本語](ai-team.ja.md)

## Current assignment and verification — 2026-10-22

dot scopes and assigns the owner's task, verifies the returned result, tests, PR and CI, and reports to the owner for acceptance. Task direction and connection availability decide the worker and Windows or cloud environment. Claude implementation followed by independent Codex verification is one pattern; an explicit owner assignment can instead make Codex responsible for implementation, tests and PR. Preserve separate-provider review where available. Do not infer universal model priority or live automation from the dated role table below.

Public code and synthetic tests are kept apart from private real data. An environment failure may be addressed only through another permitted and independently authorized route; an authorization denial is not bypassed.

> Operating snapshot: 2026-10-13 (dated; the table below is partly updated by the 2026-10-15 section); model names are owner-reported labels

## Limited final escalation — 2026-10-15

If a hard problem stalls under owner-selected GPT/Sol (usually GPT-6.1 Sol Medium) — the same failure repeats or no concrete progress within the agreed work limit — the owner may make one bounded, final escalation to **Claude Opus 5.5 Medium**. This is owner operating judgment, not a claim that Opus is objectively best or always better than Sol. Routine implementation stays with Claude or Antigravity Sonnet; Codex designs, coordinates and reviews; the owner accepts. Preserve the evidence first, check capacity/cost, record requested vs observed model/effort, respect permissions/TLS/secrets/paid approvals, then return to the ordinary model. The RunPod Phase 2 connection pass with Opus is an **owner report**, not independently confirmed, and does not accept A100 review quality or automated operation. Mattermost is only a hard-problem example. See [2026-10-15 decision](operating-decisions-2026-10-15.md).

## Planned Gemini 4 Argon expansion — 2026-10-14

Once its real availability within Antigravity is verified, Gemini 4 Argon becomes a candidate for ordinary coding, tests, UI/APIs and small fixes in addition to PoCs/mocks. Claude focuses on difficult implementation/escalations; Chappy/Codex retains complex design and scoped separate PR review; Dottie remains PM and Qwen's independent review remains unaccepted. This is a future routing proposal, not a verified deployment, model identifier, or guaranteed level of engineering seniority. [Detailed rollout and flow](gemini-4-argon-rollout.md).

## Team

| Worker / environment | Candidate work | Boundary |
|---|---|---|
| Owner | Goals, priorities, accountable approval, final acceptance and publication decisions | Verify outputs and retain relevant specialists |
| Dottie | Short requirements, acceptance criteria, allocation, progress and handoff | Not the standing long-form author or autonomous dispatcher |
| Codex / ChatGPT (Chappy) | Complex initial design, difficult decisions, final escalation and bounded Codex Review | Do not routinely rewrite or comprehensively re-review every deliverable |
| Claude Code | Implementation, fixes, tests, technical docs, blog drafts/editing/translation, GitHub docs and PR preparation | Check availability, fit and fresh capacity; publication/production actions need appropriate authorization |
| Gemini / Antigravity | Research, official-source checks, comparison tables, summaries, chart data, PoCs/mocks, alternative prose and independent first review | Allocate with Claude using the same criteria; different tools may share a provider |
| Local Qwen (Windows / Mac) | Authorized specialist research and source organization, including permitted security/social topics where suitable | Verify model capabilities, search and source checks per environment; never bypass safety controls |
| RunPod A100 Qwen | Future independent-review candidate | Live operation and quality are not accepted; use Codex Review or Claude / Antigravity different-provider review for now |

## Dottie and workflow layers

Dottie is the PM, not a claim that all task execution is automatic. Dottie clarifies scope and acceptance, selects an eligible provider/environment, tracks progress, and coordinates review and handoffs.

- **AI Governance Control** is the thin reusable handoff/artifact/evidence layer. Minimal-handoff verification is recorded in [PR #29](https://github.com/moruku36/ai-governance-control/pull/29), merged at `4fb014a`, with Ubuntu/Windows quality gates and offline container-boundary verification.
- **AIteamBridge** is the separate local capacity/router/transport engineering project. Reported status: 246 local/offline tests, uncommitted/unpublished; live quota collection and autonomous dispatch are unverified.
- These projects have complementary responsibilities; they are not three fully automated orchestrators.

### Runtime topology

- Windows is the always-on local base and first choice. Consult the user before switching to Mac if Windows cannot proceed.
- Mac is a helper environment.
- Manual CodexBar image review is in use. Automated quota retrieval and fully automatic routing are not verified.

## Chappy and Codex

Use Codex / ChatGPT for complex initial design, difficult decisions, final escalation when needed (a 2026-10-13 snapshot; see the limited Opus step in the [2026-10-15 decision](operating-decisions-2026-10-15.md) for hard problems stalled under owner-selected GPT/Sol) and bounded Codex Review for Claude/Gemini PRs; full-text rewrites and comprehensive re-review of every deliverable are not the default. Routine OpenAI selection uses only **GPT-6 Luna / Medium** or **GPT-6.1 Sol / Medium**. Choose Luna Medium for bounded work and Sol Medium when complexity or the quality bar warrants it; there is no Low/Medium/High six-step ladder. ExtraHigh remains outside the policy. Astra is an exception only when academic research or particularly difficult advanced investigation needs it, with a concrete reason; use Sol Medium when sufficient. These are owner-reported labels, not CLI IDs or proof of runtime availability.

If actual worker selection or runtime confirmation is unavailable, report the limitation and `UNKNOWN`.

## Claude Code

Candidate work includes implementation, fixes, tests, technical docs, blog drafts/editing/translation, GitHub docs and PR preparation. Retain the usual Sonnet 5.5 / harder-work Opus 5.5 labels. Check availability, fit and fresh capacity; deployment needs appropriate authorization. Native Claude Code and Claude inside Antigravity have separate pools but share a provider.

## Gemini / Antigravity

Candidate work also includes research, official-source checks, comparison tables, summaries, chart data, PoCs/mocks, alternative prose and independent first review. Allocate with Claude by fit, fresh capacity and availability rather than a fixed order. Respect task-specific choices and separate reviewer/provider from the author where possible.

## Qwen environments

- **Local:** Windows Open WebUI/Ollama text responses were owner-checked. Mac Open WebUI 0.11.4 with Qwen2.5 3B has past observations of local responses and web-search results. Search availability and specialist-research quality require environment-specific checks; this is not automated orchestration.
- **RunPod Phase 1:** [PR #39](https://github.com/moruku36/qwen-multimodal/pull/39) records one real response from small Qwen2.5-1.5B-Instruct and Pod deletion. It does not accept A100 independent-review quality or the complete workflow.
- **RunPod Phase 2:** *(2026-10-13 snapshot: mock/offline only. Since 2026-10-15 an owner report of a passed connection test with Claude Opus 5.5 Medium exists; it is unconfirmed by independent logs and is not review-quality or operation acceptance.)* Live A100 independent review, quality and ongoing operation are not accepted. Use Codex Review or Claude / Antigravity different-provider review for now. The conversational label “around 3.7” is unresolved and is not a model ID.
- **Colab:** The fixed-Q8 chat notebook is separate. [PR #35](https://github.com/moruku36/qwen-multimodal-colab/pull/35) reports 287 CPU CI checks (2 skipped), not Colab/GPU inference, model-download or A100-quality verification.
- OpenAI-compatible describes an API shape, not paid OpenAI. A single HTTP response does not establish automatic startup, connection and termination. Pod stop and deletion differ, including storage costs and data retention. This documentation change starts no GPU and changes no runtime settings.

## Allocation and failures

1. Record the goal, completion criteria, small input, worker, one alternative, planned budget/work limit, and artifact/evidence for each task.
2. Confirm the authorized route is available and actually working. Separate subscription/API and provider pools, timestamped session/weekly capacity, and reset times. Missing/stale values are `unknown`. Do not add unlike provider token units to equalize work.
3. First allocate to a fitting Claude / Antigravity candidate with available capacity. The role table is not a fixed assignment. Manual rotation when observations are stale is a proposal to reduce concentration, not proof of sufficient capacity.
4. After one failed handoff, preserve the cause and artifacts. Stop on authorization denial; do not bypass it through another route. For ordinary availability failures, consider one other authorized candidate. If none works, mark `blocked` / awaiting owner handoff; do not automatically return to full-text Codex substitution. Record a short reason for exceptions.
5. Separate builder/author and reviewer by provider where possible. Claude inside Antigravity and native Claude Code have separate pools but share a provider. Review the specified scope, evidence and major unknowns; use bounded Codex Review for Claude/Gemini code PRs, and Claude/Gemini review for Codex-built PRs.

## Quota-aware selection

1. Distinguish session and weekly windows, and record when each observation was made.
2. Direct Claude Code, Antigravity Claude/GPT, Antigravity Gemini, and native Codex are distinct capacity pools. API charges are not subscription quota.
3. No observed activity for five hours does not establish a 100% reset.
4. Missing/stale evidence is `unknown`; use an explicit or manual selection instead of inferring.
5. Consider difficulty, quality, environment, observation freshness, consumption pace, reset window, and cost; fixed thresholds alone are insufficient.
6. Never publish quota images, exact balances, account spending, credentials, or private session data.

## Communication names

Use Dottie, Chappy, Claude Code, Gemini/Antigravity, and Qwen as role labels when the context is clear. Convert a conversational request into a task-specific tool selection, and keep the requested model/effort separate from observed runtime. Do not invent CLI identifiers.

See the [2026-10-13 operating decisions](operating-decisions-2026-10-13.md) and [routing guide](routing-guide.md).

## PR Review Pipeline — 2026-10-13

Apply the [Codex Review / PR Review Pipeline](pr-review-pipeline.md) to code PRs. Codex reviews Claude/Gemini changes; another provider reviews Codex changes. Bind review and CI to the same head SHA. Comprehensive re-review of ordinary prose/research remains outside the default. Medium/high risk requires human acceptance; low-risk auto-merge is conditional on explicit policy, configuration and verification. Qwen review quality remains unaccepted; automatic review, enforced CI and auto-merge are runtime pending.
