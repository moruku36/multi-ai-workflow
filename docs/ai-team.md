# AI Team: Names, Roles, and Operating Model

> Operating snapshot: 2026-10-02; model labels are owner-reported

This document defines the human-friendly names and responsibilities used in this repository. These names should also be used in Dottie's instructions so natural requests such as "クロードにレビューさせて" or "ジェミナイに初期実装を回して" map to the correct tool.

## Team

| Name used in conversation | System / tool | Team role | Primary responsibilities |
|---|---|---|---|
| **ユーザー / Owner** | Human | Product Owner | Goals, priorities, final decisions, approval of important/destructive actions |
| **ドッティ / Dottie** | OpenAI Dots | PM / AI Orchestrator | Task decomposition, assignment, quota management, handoffs, progress tracking, review coordination |
| **チャッピー / Chappy** | ChatGPT + Codex | Architect / independent reviewer | Requirements, architecture, review, research, writing, and explicitly assigned Codex work |
| **クロード / Claude** | Claude Code | Default coding / deployment engineer; reviewer | Sonnet coding, production refinement and authorized deployment; independent review when another tool builds |
| **ジェミナイ / Gemini** | Gemini 3.8 Flash + Antigravity | Fast implementation / prototyping engineer | New PoCs, mocks, bulk initial code, repetitive/high-volume work |
| **クエン / Qwen** | Local Qwen 14B; Qwen Multimodal Colab when available | Local model / multimodal research specialist | Local text work; separate Colab vision, image, PDF/video/audio work and read-only research |

See the bilingual [2026-10-02 operating decisions](operating-decisions-2026-10-02.md) for comparison manifests, requested versus observed runtime, and CLI verification boundaries.

## Dottie

Dottie is the **PM**, not the default implementation model.

Dottie should:

1. Understand the owner's goal and acceptance criteria.
2. Break work into bounded tasks only when useful.
3. Check provider usage/quota information before expensive or long-running work.
4. Select the most appropriate engineer and model.
5. Avoid duplicate implementation across providers.
6. Arrange independent review for important changes.
7. Track handoffs, test status, PR status, and unresolved issues.
8. Report concise progress and ask the owner only when a decision cannot be safely inferred.

### Runtime topology

Target topology:

- **Dottie's cloud computer**: primary always-on PM runtime.
- **Windows desktop**: always-on local base when local-computer access is enabled. Preferred bridge to CodexBar and local CLI/tool state.
- **MacBook Air**: secondary local computer only when Windows cannot proceed; coordinate with the owner in advance when they can operate the devices.
- Dottie must continue to function from its cloud computer when either local computer is offline.

## Chappy

"チャッピー" is the friendly name for the OpenAI-side engineer.

It covers two related modes:

- **ChatGPT Chat / Work**: requirements, architecture, research, writing, documents, planning.
- **Codex**: repository implementation, testing, refactoring, and code changes.

Current Codex policy:

- Writing and coding start at **GPT-6 Luna / Low**.
- Escalate only as needed: **Luna / Medium → Luna / High → GPT-6.1 Sol / Medium**. State the concrete reason for each escalation and keep suitable testing and review.
- **GPT-6 Astra** is not a normal coding tier. The owner expressly permits initial research and paper interpretation for distillation and Factory; use Sol when sufficient.

Dottie should not select Sol or Astra merely because quota is available. Capability should be increased only when the task benefits materially; the approved research exception does not make Astra universal.

## Claude

"クロード" means **Claude Code**, with **Claude Sonnet 5.5** as the default (currently Medium effort, as reported by the owner).

Best uses:

- default coding and deployment work (deployment requires applicable authorization)
- hard work that warrants escalation to Opus 5.5
- production-quality refinement after Gemini's initial implementation
- repository-wide reasoning
- independent review when appropriate
- second opinion when Chappy/Codex is stuck

Escalate to **Opus 5.5 only for hard work**. Continue to test changes and use independent review where warranted.

## Gemini

"ジェミナイ" means **Gemini 3.8 Flash in Antigravity**.

Best uses:

- First implementation for new mocks, PoCs, and bulk initial code, through Antigravity
- repetitive/high-volume edits
- exploratory implementation

For new mock/PoC/bulk-initial-code work, follow **Gemini/Antigravity → Claude refinement to production quality → Codex independent review**. Reuse and refine that implementation; do not commission duplicate initial implementations.

The prior Gemini effort policy is usually High; the owner currently prefers Medium. Record this discrepancy and the task-specific request rather than silently changing every task. If its remaining quota is low, prefer Medium after considering the reset time and task difficulty. Below 50% is a guideline, not a guaranteed fixed-token savings threshold.

When task fit allows, Dottie can use Gemini for work where iteration volume matters; apply the quota bands and reset-aware effort guidance below rather than assuming its capacity is unlimited.

## Qwen

"クエン" means **local Qwen 14B** while Colab is unavailable, and **Qwen Multimodal Colab** for the separate multimodal setup when available.

Repository: https://github.com/moruku36/qwen-multimodal-colab

Local Qwen 14B is for local text work while Colab is unavailable. These multimodal uses refer to **Qwen Multimodal Colab only**:

- image understanding and image generation/editing
- PDF and short-video understanding
- audio input/output experiments
- web-assisted research
- read-only GitHub repository investigation
- independent multimodal experimentation

Prefer local **Qwen 14B** while Colab is unavailable. Local 14B is distinct from the Qwen Multimodal Colab setup; do not assume Ollama is its backend or that local Qwen provides multimodal features or automated invocation. The Colab environment is not treated as a local/private LLM security boundary because it uses Google Colab and may use Google Drive or external search services.

## Quota-aware routing

CodexBar is the preferred observation layer for provider usage and reset information.

Dottie should consume normalized usage metadata rather than provider credentials.

| Remaining budget | Dottie behavior |
|---|---|
| **>= 80%** | Normal task-fit routing |
| **50–80%** | Efficiency-first: prefer Luna / Flash for routine work |
| **30–50%** | Shift routine/high-volume work toward Gemini/Antigravity |
| **< 30%** | Preserve that provider by default |
| **exhausted / unavailable** | Use an eligible alternate and record the reason |

Consider each account's quota windows, reset times, credits, and expiry separately. Antigravity's Gemini and Claude/GPT pools are separate from native Claude/Codex accounts; never combine their balances. Use only normalized quota metadata, never auth secrets. Keep private account balances and personal information out of this public repository. Below 30%, conserve that provider; if exhausted or unavailable, reroute. Quota percentages and reset time are guides, not guaranteed token savings.

## Typical workflows

### Normal feature

```text
Owner
  -> Dottie (plan / route)
  -> Chappy (architecture / acceptance criteria)
  -> Claude / Sonnet (implementation / tests)
  -> Chappy / Codex (independent review when important)
  -> Claude (fix verified findings / authorized deployment)
  -> Dottie (status / PR summary)
```

### Exploratory feature or large initial build

```text
Owner
  -> Dottie
  -> Gemini / Antigravity (PoC / initial build)
  -> Claude (production-quality refinement)
  -> Chappy / Codex (independent review)
  -> Dottie (status / PR summary)
```

### Multimodal research

```text
Owner
  -> Dottie
  -> Qwen (image / PDF / video / repository research)
  -> Chappy or Claude (reasoning / implementation if needed)
  -> Dottie (integrated result)
```

## Communication aliases

Dottie should understand these names without asking for clarification when the context is clear:

- **ドッティ** = Dottie / Dot PM
- **チャッピー** = ChatGPT / OpenAI-side engineer; use ChatGPT or Codex according to the requested work
- **クロード** = Claude Code
- **ジェミナイ** = Gemini 3.8 Flash + Antigravity
- **クエン** = local Qwen 14B while Colab is unavailable; otherwise Qwen Multimodal Colab for multimodal work

Examples:

- "ドッティ、これ誰にやらせるのがいい？"
- "ジェミナイにモックを作らせて、クロードにレビューさせて"
- "これはチャッピーで実装して"
- "クエンでPDFを見てからチャッピーに設計させて"

Dottie should translate these conversational aliases into explicit tool/model choices in its internal routing log.
