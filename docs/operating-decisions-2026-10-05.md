# AI Team Operating Decisions — 2026-10-05

[English](operating-decisions-2026-10-05.md) | [日本語](operating-decisions-2026-10-05.ja.md)

This public record summarizes operating guidance and evidence boundaries. Model labels are owner-reported; they do not establish API identifiers, exact runtime models, or availability in a particular CLI. No private account values, conversations, or logs belong here.

## Roles and routing

Windows is the always-on local base and first choice. Consult the user before switching to Mac if Windows cannot proceed.

| Role | Responsibility |
|---|---|
| Product Owner | Goals, priorities, acceptance, and decisions |
| Dottie | PM: task specification, provider/environment choice, progress, and acceptance tracking |
| Chappy | Architect and reviewer; may perform assigned ChatGPT/Codex work |
| Claude Code | Usual coding/deployment engineer: Sonnet 5.5 by default, Opus 5.5 when warranted |
| Gemini / Antigravity | Candidate for PoCs/mocks and suitable implementation tasks; choice is task-specific |
| Qwen | Local text and separate multimodal research environments |

Select based on task difficulty, quality needs, environment, fresh quota evidence, consumption pace/reset window, and cost. Respect an explicit task-level choice. There is no global Antigravity-Claude-first rule.

Codex is used when it fits the task or the owner assigns it. Its effort sequence is Luna/Low → Luna/Medium → Luna/High → GPT-6.1 Sol/Low → Sol/Medium → Sol/High. ExtraHigh is not used. Astra is not a routine coding tier; it is reserved for individually justified advanced academic/technical analysis, with Sol when sufficient.

## Capacity and observation

- Distinguish session and weekly windows; do not combine used/remaining values across windows.
- Record observation time and freshness. No observed activity for five hours does not establish a 100% reset.
- CodexBar quota images are reviewed manually. Automated quota retrieval and complete automatic routing remain unverified.
- Antigravity Gemini, Antigravity Claude/GPT, direct Claude Code, and native Codex pools are separate. API charges are not subscription quota.
- Missing or stale readings are `unknown`; do not infer or publish exact balances, costs, screenshots, credentials, or account details.

## System boundaries and dated evidence

- **Dottie** performs PM work. **AI Engineering Factory** supplies a thin reusable handoff/artifact/evidence layer. Its minimal handoff was verified in [Factory PR #29](https://github.com/moruku36/ai-engineering-factory/pull/29), merged at `4fb014a`, including Ubuntu/Windows quality gates and offline container-boundary verification.
- **AIteamBridge** is a separate capacity/router/transport implementation project. Reported state: local/offline, 246 tests, uncommitted/unpublished; live autonomous quota retrieval and dispatch are unverified. Recheck the Bridge repository before revising this dated observation.
- These three roles are complementary; do not portray them as duplicate fully automatic orchestrators.
- One supervised Antigravity web session showed a task request and response; the retrieved result reported 324 unit checks and 25 mock browser checks. This single result does not prove CLI operation, general automatic routing, or independent test reproduction.
- Windows local CLI received an access-denied response; its root cause is unknown and its use remains unverified. The local CLI and web route are different paths.
- Windows Open WebUI/Ollama text responses were checked by user operation. Mac Open WebUI 0.11.4 plus local Qwen2.5 3B returned local responses and web-search results. These are not automated orchestration.
- The fixed-Q8 Colab chat notebook preserves the original multimodal setup. [Qwen Multimodal Colab PR #35](https://github.com/moruku36/qwen-multimodal-colab/pull/35) reports 287 CPU CI tests (2 skipped). No Colab/GPU inference or model download was run; A100 quality, speed, VRAM, and compute use remain deferred.
- [Qwen RunPod Operations PR #1](https://github.com/moruku36/qwen-runpod-operations/pull/1) is documentation-only. The latest chat candidate has Linux CPU validation; CUDA, model download, and inference are runtime-pending.
- WebUI → OpenAI-compatible API → on-demand RunPod Qwen is a target design. Starting a Pod, HTTP connection, and automatic termination are unverified. OpenAI-compatible describes an API shape, not paid OpenAI usage. Stopping a Pod differs from deleting it; persistent storage may incur charges after stop, and deletion may lose data.

## Evidence states

Use these states consistently in both languages:

- **verified/merged**: evidence confirms the stated test or merged documentation/code.
- **local/offline**: tests or behavior were checked locally without proving a live provider/runtime path.
- **runtime pending**: intended live/CUDA/download/inference/dispatch behavior has not been verified.
- **proposal**: a target design or future work, not implemented behavior.

User approval, execution-environment authorization, local test success, and deployment/runtime reflection are separate stages. On a rejected approval, retain the work and stop at the proper path. Do not spam re-approval or route around rejection.

For GitHub code changes, update the affected README, usage, and design documentation, including existing English/Japanese counterparts. Keep both languages aligned on evidence and implementation status.

## Public documentation boundary

Publish only general operating constraints. Exclude private conversations/history, personal or family details, secrets, login destinations, quota screenshots, exact balances/account data, and private logs. This documentation task does not require installing services, paid usage, API-key creation, or application execution-configuration changes.
