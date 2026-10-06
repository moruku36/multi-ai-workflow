# AI Team: Names, Roles, and Operating Model

[English](ai-team.md) | [日本語](ai-team.ja.md)

> Operating snapshot: 2026-10-06; model names are owner-reported labels

## Team

| Name | System / tool | Role and responsibility |
|---|---|---|
| Owner | Human | Product Owner: goals, priorities, acceptance, and decisions |
| Dottie | OpenAI Dots | PM: task specification, provider/environment selection, progress, acceptance, and handoff coordination |
| Chappy | ChatGPT + Codex | Architect/reviewer; research, writing, and assigned repository work |
| Claude | Claude Code | Usual coding/deployment engineer: Sonnet 5.5 by default, Opus 5.5 for hard work |
| Gemini | Gemini + Antigravity | Candidate for PoCs, mocks, and suitable implementation tasks; no fixed model route |
| Qwen | Local Open WebUI/Ollama; separate Colab setup | Local text and multimodal research in distinct environments |

## Dottie and workflow layers

Dottie is the PM, not a claim that all task execution is automatic. Dottie clarifies scope and acceptance, selects an eligible provider/environment, tracks progress, and coordinates review and handoffs.

- **AI Engineering Factory** is the thin reusable handoff/artifact/evidence layer. Minimal-handoff verification is recorded in [PR #29](https://github.com/moruku36/ai-engineering-factory/pull/29), merged at `4fb014a`, with Ubuntu/Windows quality gates and offline container-boundary verification.
- **AIteamBridge** is the separate local capacity/router/transport engineering project. Reported status: 246 local/offline tests, uncommitted/unpublished; live quota collection and autonomous dispatch are unverified.
- These projects have complementary responsibilities; they are not three fully automated orchestrators.

### Runtime topology

- Windows is the always-on local base and first choice. Consult the user before switching to Mac if Windows cannot proceed.
- Mac is a helper environment.
- Manual CodexBar image review is in use. Automated quota retrieval and fully automatic routing are not verified.

## Chappy and Codex

Use Codex when it fits the task or is explicitly assigned. Routine OpenAI selection uses only **GPT-6 Luna / Medium** or **GPT-6.1 Sol / Medium**. Choose Luna Medium for bounded work and Sol Medium when complexity or the quality bar warrants it; there is no Low/Medium/High six-step ladder. ExtraHigh remains outside the policy. Astra is an exception only when academic research or particularly difficult advanced investigation needs it, with a concrete reason; use Sol Medium when sufficient. These are owner-reported labels, not CLI IDs or proof of runtime availability.

If actual worker selection or runtime confirmation is unavailable, report the limitation and `UNKNOWN`.

## Claude Code

Use Sonnet 5.5 for usual coding and deployment work. Use Opus 5.5 when task difficulty warrants it. Deployment still requires the appropriate authorization. Direct Claude Code and Claude inside Antigravity consume separate pools.

## Gemini / Antigravity

Gemini/Antigravity is one suitable option for PoCs, mocks, or implementation; it is not a fixed first stop. Choose the model and effort for the particular task, quality need, environment, fresh capacity evidence, and cost. Respect a task-specific user choice without converting it into a global default.

## Qwen environments

- Windows Open WebUI/Ollama text responses have been checked through user operation.
- Mac Open WebUI 0.11.4 with local Qwen2.5 3B returned local responses and web-search results. This is not automated orchestration.
- The fixed-Q8 Colab chat notebook preserves the original multimodal setup. [PR #35](https://github.com/moruku36/qwen-multimodal-colab/pull/35) reports 287 CPU CI tests (2 skipped); no Colab/GPU inference or model download was run. A100 quality, speed, VRAM, and compute use remain deferred.
- One supervised Antigravity web session showed a task request and response; the retrieved result reported 324 unit checks and 25 mock browser checks. This single result does not prove CLI operation, general automatic routing, or independent test reproduction.
- RunPod Operations PR #1 is documentation-only. The current chat candidate is Linux CPU-validated; CUDA, model download, and inference remain pending.
- WebUI → OpenAI-compatible API → on-demand RunPod Qwen is a target design, not verified runtime behavior. OpenAI-compatible is not paid OpenAI. Stop and deletion differ; persistent storage may incur charges after stop and deletion may lose data.

## Quota-aware selection

1. Distinguish session and weekly windows, and record when each observation was made.
2. Direct Claude Code, Antigravity Claude/GPT, Antigravity Gemini, and native Codex are distinct capacity pools. API charges are not subscription quota.
3. No observed activity for five hours does not establish a 100% reset.
4. Missing/stale evidence is `unknown`; use an explicit or manual selection instead of inferring.
5. Consider difficulty, quality, environment, observation freshness, consumption pace, reset window, and cost; fixed thresholds alone are insufficient.
6. Never publish quota images, exact balances, account spending, credentials, or private session data.

## Communication names

Use Dottie, Chappy, Claude Code, Gemini/Antigravity, and Qwen as role labels when the context is clear. Convert a conversational request into a task-specific tool selection, and keep the requested model/effort separate from observed runtime. Do not invent CLI identifiers.

See the [2026-10-06 operating decisions](operating-decisions-2026-10-06.md) and [routing guide](routing-guide.md).
