# Legacy: Ollama / Qwen (+ Open WebUI)

[English](README.md) | [日本語](README.ja.md)

This directory retains an older local setup. It is not an automatic orchestration stack.

## Current local observations

- Windows text through Open WebUI/Ollama has received a user-operated response check.
- Mac Open WebUI 0.11.4 with a small local Qwen2.5 3B has returned local responses and web-search results.
- These checks do not mean every script here is currently in use, that local quota routing exists, or that requests are automatically orchestrated.
- The separate fixed-Q8 Colab chat notebook preserves the original multimodal setup. See [Qwen Multimodal Colab](https://github.com/moruku36/qwen-multimodal-colab); do not infer that local Qwen has those Colab features.

Scripts such as `Modelfile`, `run.sh`, `run.ps1`, and `start-webui.bat` remain for legacy/reference use. Check the actual files and local environment before relying on them.

## Environment distinction

| Property | Local Open WebUI/Ollama | Qwen Multimodal Colab |
|---|---|---|
| Runtime | Windows or Mac local environment | Google Colab notebook |
| Verified here | User-operated text response; Mac local 3B response and web-search result | PR #35 reports 287 CPU CI tests (2 skipped); no Colab/GPU inference or model download was run |
| Multimodal capabilities | Do not infer from Colab | Notebook-specific image/PDF/audio/video capabilities |
| Automation | Not established | Not implied by notebook verification |

See the [current routing guide](../../docs/routing-guide.md) and [operating record](../../docs/operating-decisions-2026-10-06.md).
