# Multi-AI Workflow Architecture

[English](README.md) | [日本語](README.ja.md)

Operational guidance for assigning research, reasoning, initial implementation, production implementation, independent review, and multimodal experiments across ChatGPT, Codex, Claude Code, Gemini/Antigravity, and Qwen Colab.

## Workflow

Use research and design to establish requirements, assign a bounded implementation task to one tool, run independent review, and verify the result before integration. The repository also covers writing, presentations, research, and multimodal work.

The recorded model snapshot is 2026-10-01. Codex writing and coding start at GPT-6 Luna / Low and escalate through Luna Medium, Luna High, then GPT-6.1 Sol / Medium only when needed; explain why each escalation is warranted and retain appropriate testing and independent review. Astra is reserved, not a routine tier. Claude defaults to Sonnet 5.5 (currently Medium effort, as reported by the owner); use Opus 5.5 only for hard work. For new mocks, PoCs, and bulk initial code, use Gemini 3.8 Flash through Antigravity first, Claude for production-quality refinement, and Codex for independent review. Keep existing repairs with the best-fit tool, follow the user's explicit choice, and avoid duplicate initial implementations.

## Operating rules

Keep tasks bounded, avoid assigning the same implementation twice, preserve usage budgets, and separate implementation from independent review. **Dottie** is the PM/orchestrator: Chappy (ChatGPT/Codex), Claude, Gemini/Antigravity, and Qwen are the engineering team. Windows is the primary local base; use the Mac only when Windows cannot proceed and coordinate availability first. Antigravity's Gemini and Claude/GPT quota pools are separate from native Claude/Codex accounts; never merge their balances. Route using only quota metadata, never credentials or private account balances in this public repository. Confirm capabilities in use: an installed GUI does not prove remote control or CLI authentication. Security-sensitive changes need approval; never bypass EDR.

```bash
cp templates/.env.example .env
```

Inspect `configs/`, `templates/`, `tools/`, and the recipes in `docs/` before configuring the workflow.

## Execution Security (optional)

Task Routing decides **who** does the work. Below it sits an optional **Execution Security** layer that decides **what that agent is allowed to do**. [OpenShell Claude Reviewer](https://github.com/moruku36/openshell-claude-reviewer) runs the Claude Code reviewer inside an NVIDIA OpenShell sandbox. OpenShell is not a model tier and does not change routing or model selection.

- **Builder (Codex)** implements and may write to the repository and open PRs.
- **Reviewer (Claude Code, optionally in OpenShell)** reads the repository only. GitHub writes (push, PR/issue writes) are denied by policy, not by prompt.
- Use the OpenShell reviewer for important repositories and security-focused reviews. Ordinary light reviews stay on plain Claude Code; OpenShell is not required for every Claude Code run.

Verification status: the sandbox boundary passed 13/13 deny checks. A real review through `review.sh` with an actual Anthropic API key has **not been verified yet**. See the [routing guide](docs/routing-guide.md#7-execution-security) for details.

## Contents

- [assets/](assets)
- [configs/](configs)
- [docs/](docs) — includes [AI team roles](docs/ai-team.md) and [Dots + CodexBar orchestration](docs/dots-codexbar-orchestration.md)
- [templates/](templates)
- [tools/](tools)

## Detailed documentation

The [Japanese guide](README.ja.md) retains the complete original setup instructions, configuration, examples, project status, and limitations. Supporting documents keep their existing language.
