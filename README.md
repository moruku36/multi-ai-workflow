# Multi-AI Workflow Architecture

[English](README.md) | [日本語](README.ja.md)

Operational guidance for assigning research, reasoning, initial implementation, production implementation, independent review, and multimodal experiments across ChatGPT, Codex, Claude Code, Gemini/Antigravity, and Qwen Colab.

## Workflow

Use research and design to establish requirements, assign a bounded implementation task to one tool, run independent review, and verify the result before integration. The repository also covers writing, presentations, research, and multimodal work.

The recorded model snapshot is 2026-09-30. It uses GPT-6 Luna as a standard option, raises effort or model capability when needed, and assigns Claude Code, Gemini/Antigravity, and Qwen Colab according to role and task. These are the owner's dated operating choices.

## Operating rules

Keep tasks bounded, avoid assigning the same implementation twice, preserve usage budgets, and separate implementation from independent review. **Dottie** is the PM/orchestrator: Chappy (ChatGPT/Codex), Claude, Gemini/Antigravity, and Qwen are the engineering team. Dottie uses CodexBar usage data as the planned quota-observation layer for routing.

```bash
cp templates/.env.example .env
```

Inspect `configs/`, `templates/`, `tools/`, and the recipes in `docs/` before configuring the workflow.


## Contents

- [assets/](assets)
- [configs/](configs)
- [docs/](docs) — includes [AI team roles](docs/ai-team.md) and [Dots + CodexBar orchestration](docs/dots-codexbar-orchestration.md)
- [templates/](templates)
- [tools/](tools)

## Detailed documentation

The [Japanese guide](README.ja.md) retains the complete original setup instructions, configuration, examples, project status, and limitations. Supporting documents keep their existing language.
