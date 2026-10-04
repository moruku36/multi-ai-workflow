# Tools: Legacy Ollama + Claude Review CLI

> **Legacy:** the Ollama→Claude API pipeline is not a normal path in the current workflow. This page documents retained code, not an active orchestration service.

`pipeline.py` can draft with local Ollama and send a review request through the Claude API. It is retained for legacy/reference use.

## Current routing context

- For code changes, select an appropriate Codex, Claude Code, or Antigravity route per the [routing guide](../docs/routing-guide.md).
- For local text, Windows Open WebUI/Ollama has had a user-operated response check; a Mac local setup has also returned responses. These checks do not establish automatic orchestration.
- Dottie, Factory, and AIteamBridge have different PM, handoff/evidence, and local capacity/router/transport responsibilities. Bridge live quota retrieval and autonomous dispatch remain unverified.
- Independent review uses a tool different from the builder when warranted. Claude Code commonly uses Sonnet 5.5; Opus 5.5 is for hard work.

## Legacy CLI modes

1. `chain`: draft locally with Ollama, then request a Claude API review.
2. `clean`: draft locally with Ollama only.
3. `review`: request Claude API review only.

The historical review model configured by this legacy script may not match current product availability or operating choices. Verify before use; do not infer a subscription entitlement from API configuration.

```bash
export ANTHROPIC_API_KEY="your-api-key"
python tools/pipeline.py proposal.md --mode review -o review_report.md
```

Only use the Ollama setup when intentionally using this legacy path; see [`configs/level1-ollama/`](../configs/level1-ollama/).
