# Multi-AI Workflow Architecture

[English](README.md) | [日本語](README.ja.md)

Public guidance for coordinating implementation, review and reporting across authorized tools. The model names in dated sections are owner-reported operating labels, not verified service specifications or runtime identities.

This repository is the public record of how one owner runs several AI agents as a single team: who does what, how they hand work to each other, and what has been verified. It starts with the current architecture and the latest update; everything older lives in dated documents below, reachable from the repository map.

## Latest communication status — 2026-11-06

[Kurotchi, Dots and Muse: verified stages and remaining work](docs/communication-status-2026-11-06.md). Kurotchi mailbox reading and one manual receipt are evidenced; scheduled execution is observed. Automatic round-trip replies and a common three-party 30-minute cadence remain unverified. The November 2 architecture below is a historical snapshot, not proof that every link is live today.

## Current architecture — 2026-11-02

The mesh is centered on a private GitHub repository, **agent-lounge**, which acts as the mailbox and request board between the resident agents. Fuwatchi (Muse, Meta's personal agent) works from the cloud and reaches the lounge by polling; its role is direction, design, review and confirmation — the owner's daily window and the media desk (articles, videos) — while hands-on writing and building are delegated to connected APIs and other agents. Dots, the OpenAI resident agent on the Windows machine, is woken by GitHub notifications and leads the home-lab build and operations work. The Windows coding squad (Claude Code, Codex, Antigravity) takes work through `LOUNGE-*` issues. Model APIs (MiMo, Meta, OpenAI, Baseten) never initiate contact; they are called through GitHub Actions event routes or directly by a resident agent.

Two environments were added around 2026-11-01–02. The cloud development environment **midorun** on OCI (built 2026-11-01) runs Claude Code, and Claude Code (CLI) is the development axis for both the cloud environment and the home lab (decided 2026-11-02); Anthropic access is API-based as the basic stance. The home lab gained a Mac mini (M4, arrived 2026-11-01) as an experiment host for multiple AIs, with **OpenClaw** (open-source, self-hosted) as its orchestration gateway. The lab-operations agent **Kurocchi** runs on OpenClaw (selected 2026-11-01) and starts read-only: monitoring → triage → approved procedures → verification. The owner's daily contact channel is LINE; lab-operations notifications go to Discord. Antigravity is used only through the official client on the owner's own devices and is not deployed into the OCI environment or OpenClaw (decided 2026-11-02, after public reports of account suspensions tied to third-party OAuth use).

The full diagram is below, reflecting the state as of 2026-11-02. The per-link inventory, cadences and verification status as of 2026-10-30 live in the [network topology snapshot](docs/network-topology-2026-10-30.md) ([日本語](docs/network-topology-2026-10-30.ja.md)).

```mermaid
flowchart LR
    MORI["moruku36 (owner)"]

    subgraph RESIDENTS["Resident agents"]
        FUWA["Fuwatchi (Muse)<br/>cloud VM"]
        DOTS["Dots<br/>Windows resident"]
    end

    subgraph LOUNGE["agent-lounge (GitHub, private)"]
        FILES["Mailbox files<br/>to-muse.md / to-dots.md / requests/"]
        ISSUES["Issues<br/>LOUNGE-* intake"]
        ACTIONS["GitHub Actions<br/>mailbox-notify / event workflows"]
    end

    subgraph SQUAD["Coding squad (Windows)"]
        CC["Claude Code"]
        CODEX["Codex"]
        AG["Antigravity"]
    end

    subgraph APIS["API providers (called, never callers)"]
        MIMO["MiMo API"]
        META["Meta Model API"]
        OPENAI["OpenAI API"]
        BASETEN["Baseten API<br/>Muse Spark Open"]
        MODAL["Modal<br/>Gemma (GPU)"]
    end

    subgraph LAB["Home lab"]
        OC["OpenClaw<br/>gateway on Mac mini (M4)"]
        KURO["Kurocchi<br/>lab operations (read-only start)"]
        MAC["Mac mini (M4)"]
        NUC["Intel NUC"]
    end

    subgraph CLOUDDEV["Cloud development (OCI)"]
        MID["midorun<br/>Claude Code (CLI)"]
    end

    VERCEL["Applications on Vercel"]

    MORI <-->|"chat, real time"| FUWA
    MORI <-->|"local, direct"| DOTS

    FUWA -->|"write: connector push<br/>+ status share every 2 hours"| FILES
    FILES -.->|"read: polling every 30 min<br/>06:00-22:00 JST"| FUWA

    DOTS -->|"commit / push"| FILES
    FILES -->|"push event"| ACTIONS
    ACTIONS -->|"metadata comment<br/>on a fixed issue"| ISSUES
    ISSUES -->|"event: GitHub notification<br/>wakes Dots (+ hourly fallback)"| DOTS

    FUWA -.->|"creates LOUNGE-* issues<br/>on demand"| ISSUES
    ISSUES -->|"LOUNGE-CLAUDE: direct intake<br/>replies confirmed; wake-up unconfirmed"| CC
    ISSUES -->|"LOUNGE-CODEX: relayed by Dots"| CODEX
    ISSUES -.->|"LOUNGE-ANTIGRAVITY:<br/>polling every 30 min"| AG

    ISSUES -->|"issue opened event"| ACTIONS
    ACTIONS -->|"MiMo route: event-driven, verified"| MIMO
    ACTIONS -->|"Meta route: one-shot candidate,<br/>fail-closed"| META
    ACTIONS -->|"OpenAI route: one-shot candidate,<br/>fail-closed"| OPENAI

    DOTS -.->|"local call, key via 1Password<br/>no lounge route yet"| BASETEN
    FUWA -.->|"direct connector, on demand"| META
    FUWA -.->|"direct connector, on demand"| BASETEN
    FUWA -.->|"direct connector, on demand"| OPENAI
    FUWA -.->|"direct connector, on demand"| MIMO

    MORI -->|"daily contact: LINE<br/>lab notifications: Discord"| OC
    OC --> KURO
    KURO -->|"governs the home lab:<br/>monitoring → triage → approved<br/>procedures → verification"| MAC
    KURO -->|"governs"| NUC
    KURO -->|"maintains & operates<br/>the applications"| VERCEL
    DOTS -.->|"builds & operates<br/>the home lab"| OC

    FUWA -->|"built & operates"| MID
    MORI -.->|"Remote Control"| MID


    classDef user fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    classDef agent fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef hub fill:#fef9c3,stroke:#ca8a04,color:#713f12
    classDef external fill:#f3e8ff,stroke:#9333ea,color:#581c87
    classDef app fill:#ffedd5,stroke:#ea580c,color:#7c2d12
    classDef host fill:#f1f5f9,stroke:#64748b,color:#1e293b
    class MORI user
    class FUWA,DOTS,CC,CODEX,AG,OC,KURO,MID agent
    class FILES,ISSUES,ACTIONS hub
    class MIMO,META,OPENAI,BASETEN,MODAL external
    class VERCEL app
    class MAC,NUC host
```

Larger view of the current diagram (2026-11-02): [full-size PNG](assets/network-topology-2026-11-02.png). The 2026-10-30 snapshot PNG is kept at [assets/network-topology-2026-10-30.png](assets/network-topology-2026-10-30.png).

## Latest update — 2026-11-02

- **Home lab grows an orchestration layer.** A Mac mini (M4) arrived on 2026-11-01 as an experiment host for multiple AIs. OpenClaw (open-source, self-hosted) is adopted as its orchestration gateway, and the lab-operations agent Kurocchi — selected on 2026-11-01 over Hermes Agent — starts read-only: monitoring → triage → approved procedures → verification. Channels are split: LINE for the owner's daily contact, Discord for lab-operations notifications. Dots leads the home-lab build and operations work.
- **Development axis decided (2026-11-02).** Claude Code (CLI) is the axis for both the cloud development environment and the home lab. The OCI environment midorun (built 2026-11-01) runs Claude Code; Anthropic access is API-based as the basic stance.
- **Antigravity policy (2026-11-02).** Antigravity is used only through the official client on the owner's own devices; it is not deployed into the OCI environment or OpenClaw, after public reports of account suspensions tied to third-party OAuth use.
- **Roles confirmed.** Owner = PMO and final decisions; Fuwatchi (Muse) = direction, design, review and media; Dots = home-lab build and operations; coding execution = Claude Code / Codex and the connected APIs (Meta Model API, MiMo, OpenAI, Baseten, Modal).
- **Lounge cadence.** Fuwatchi's status share moved to every 2 hours on 2026-11-01; the mailbox watch stays every 30 minutes (06:00–22:00 JST).

## Update — 2026-10-30

- Added the [network topology snapshot](docs/network-topology-2026-10-30.md): the current mesh, with each link marked event-driven, polling or on-demand.
- Lounge communication cadence shortened: Fuwatchi's mailbox watch and status share now run every 30 minutes (06:00–22:00 JST), down from hourly, to cut lag. Dots remains event-driven with an hourly fallback.
- Two requests filed in the lounge: generalize the Meta and OpenAI event routes from one-shot candidates to prefix-based general routes (REQ-20251030-001), and create a Baseten lounge route (REQ-20251030-002).
- The `LOUNGE-CLAUDE:` issue intake is Fuwatchi's route to the Windows-local Claude Code; a connection test is open as lounge Issue #39. The unused `claude-lounge-one-shot` workflow file is a paper candidate, not an API route — there is no Claude API key or credit in this setup.
- This README was reorganized: dated sections moved in full to the [archive](docs/readme-history-2026-10.md); figures are Mermaid text again instead of SVG images.

## Dated updates archive

Earlier dated sections of this README (2026-10-13 → 2026-10-26) are preserved in full in [docs/readme-history-2026-10.md](docs/readme-history-2026-10.md) ([日本語](docs/readme-history-2026-10.ja.md)):

- 2026-10-26 — Proposed communication and quality foundation
- 2026-10-22 — Current operation snapshot
- 2026-10-19 — Model & efficiency operational policy; MiMo API utilization expansion
- 2026-10-16 — Daybreak models and authorized OSS security review
- 2026-10-15 — Review policy v2026.10.15-r2; Limited final escalation to Claude Opus 5.5 Medium
- 2026-10-14 — Gemini 4 Argon conditional rollout
- 2026-10-13 — Operating snapshot; Codex Review / PR Review Pipeline

## Roles and workflow boundaries

| Layer | Responsibility | Status |
|---|---|---|
| Dottie | PM: task scope, provider/environment selection, progress and acceptance | Human-directed PM role; do not imply complete autonomous dispatch |
| AI Governance Control | Reusable minimal handoff, artifacts, and evidence layer | Minimal handoff verified in AI Governance Control PR #29; it is not a second autonomous orchestrator |
| AIteamBridge | Capacity observations, routing, and transport implementation project | Local/offline stage; live quota retrieval and autonomous dispatch unverified |

These layers complement one another; they are not three overlapping, fully automated command centers. For AI Governance Control's verified minimal handoff, see [PR #29](https://github.com/moruku36/ai-governance-control/pull/29) (merged at `4fb014a`). Bridge details can change with its repository, so keep public claims limited to dated verification and generic boundaries.

```mermaid
flowchart LR
    U["Product Owner"] --> D["Dottie<br/>PM / acceptance"]
    D --> A["Selected production / research worker<br/>Claude / Antigravity / local Qwen"]
    A --> F["AI Governance Control<br/>handoff + artifacts + evidence"]
    F --> D
    B["AIteamBridge<br/>local capacity/router/transport work"] -. "not live autonomous dispatch" .-> D
```

## Quota-aware selection

- Treat session and weekly quota windows as different measurements. Used/remaining values must name their window and observation time.
- No activity for five hours does not establish a 100% quota reset. Keep old, missing, or stale observations `unknown` and fail closed to a manual choice.
- Antigravity Gemini, Antigravity Claude/GPT, and native Claude/Codex subscriptions are separate pools. API charges are not subscription quota. Never publish balances, quota screenshots, credentials, or account-specific spending.
- Weigh complexity, quality, environment constraints, freshness, consumption rate, reset timing, and cost. Fixed thresholds alone are insufficient.

## Implementation and verification status

Keep **verified/merged**, **local/offline**, **runtime pending**, and **proposal** distinct in English and Japanese. A user approval, execution-environment authorization, a passing local test, and a production/runtime change are separate stages. Do not repeatedly retry rejected approvals or use another route to bypass them; preserve the work and stop for the correct approval path.

- The AI Governance Control minimal-handoff direction is verified by PR #29 and includes Ubuntu/Windows quality gates and an offline, container-boundary verification. This does not establish live automation.
- AIteamBridge capacity/router work has been reported at 246 local/offline tests; it is uncommitted/unpublished, and live autonomous quota retrieval/dispatch is unverified. Recheck the source repository before changing this dated evidence.
- In one supervised Antigravity web session, a task request and response were observed; the retrieved result reported 324 unit checks and 25 mock browser checks. This is a single web-task result, not proof of CLI operation, general automated routing, or independently reproduced tests. Local Windows CLI status remains unverified.
- CodexBar quota-image review is manual. No claim of automatic reading or complete quota-aware routing.

## Qwen and on-demand GPU status

- **Local:** Windows Open WebUI/Ollama text responses were owner-checked. Mac Open WebUI 0.11.4 with Qwen2.5 3B has past observations of local responses and web-search results. Search availability and specialist-research quality require environment-specific checks; this is not automated orchestration.
- **RunPod Phase 1:** [PR #39](https://github.com/moruku36/qwen-multimodal/pull/39) records one real response from small Qwen2.5-1.5B-Instruct and Pod deletion. It does not accept A100 independent-review quality or the complete workflow.
- **RunPod Phase 2:** *(2026-10-13 snapshot: mock/offline only. Since 2026-10-15 an owner report of a passed connection test with Claude Opus 5.5 Medium exists; it is unconfirmed by independent logs and is not review-quality or operation acceptance.)* Live A100 independent review, quality and ongoing operation are not accepted. Use Codex Review or Claude / Antigravity different-provider review for now. The conversational label “around 3.7” is unresolved and is not a model ID.
- **Colab:** The fixed-Q8 chat notebook is separate. [PR #35](https://github.com/moruku36/qwen-multimodal-colab/pull/35) reports 287 CPU CI checks (2 skipped), not Colab/GPU inference, model-download or A100-quality verification.
- OpenAI-compatible describes an API shape, not paid OpenAI. A single HTTP response does not establish automatic startup, connection and termination. Pod stop and deletion differ, including storage costs and data retention. This documentation change starts no GPU and changes no runtime settings.

## Privacy and security

This is a public repository. Do not include private conversations, personal or family details, credentials, login destinations, quota images, exact account balances, or logs containing them. Describe only general operating constraints. Do not add services, incur charges, generate API keys, change application execution configuration, or bypass security controls as part of documentation work.

## Future study: Agent KV cache control

A [study proposal based on Cache Engineering for Agents](docs/cache-engineering-future-study.md) separates provider prompt caching, summarization and direct KV control. AKV adoption, measured savings and code changes have not occurred.

## Future idea — 2026-11-03: Customer-facing work with Claude Duet

Once Claude Duet becomes available in Japan, the idea is to assign sales, consulting and other customer-facing work to it as a group. Its proposed role in the multi-AI workflow is to handle conversations and tasks that call for consideration, politeness and care.

Availability timing in Japan is unconfirmed. This is a future idea, not a change to current responsibilities or execution permissions.

## Repository map

- [OpenClaw setup notes (Japanese)](docs/openclaw-build-notes-2026-11-05.ja.md) — dated security boundaries, observations and pending checks

- `README.md` / `README.ja.md` — this overview: what this is, the current architecture, and the latest update
- `docs/network-topology-2026-10-30.md` / `.ja.md` — network topology: who talks to whom, and how (diagram + link inventory)
- `docs/readme-history-2026-10.md` / `.ja.md` — dated updates formerly kept in this README (2026-10-13 → 2026-10-26), preserved in full
- `docs/` — guides and records: [AI team](docs/ai-team.md), [routing guide](docs/routing-guide.md), [handoff templates](docs/handoff-templates.md), [PR review pipeline](docs/pr-review-pipeline.md), [Dots / CodexBar orchestration](docs/dots-codexbar-orchestration.md), dated `operating-decisions-*`, `cookbook/`, `reports/`
- `docs/daybreak-authorized-oss-security-review.md` / `.ja.md` — Daybreak models per official docs and a proposed authorized OSS security review procedure (documented, not enabled)
- `configs/` — tool-specific guidance, including the [Open WebUI local memory runbook](configs/openwebui-local-memory-0.11.4/README.md) ([日本語](configs/openwebui-local-memory-0.11.4/README.ja.md))
- `tools/architecture/` — Mermaid sources (`.mmd`) for the diagrams in this repository; edit these, not rendered images
- `assets/` — rendered diagram files kept for reference
- `templates/` / `tests/` — environment template and quality-baseline checks

## Quick start

```bash
cp templates/.env.example .env
```

The environment template is optional for the direct client workflow; do not put credentials in public documentation.
