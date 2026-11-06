# November 2 historical snapshot

Preserved from the README. These are dated claims, not current runtime verification.

## Historical architecture — 2026-11-02

The mesh is centered on a private GitHub repository, **agent-lounge**, which acts as the mailbox and request board between the resident agents. Fuwatchi (Muse, Meta's personal agent) works from the cloud and reaches the lounge by polling; its role is direction, design, review and confirmation — the owner's daily window and the media desk (articles, videos) — while hands-on writing and building are delegated to connected APIs and other agents. Dots, the OpenAI resident agent on the Windows machine, is woken by GitHub notifications and leads the home-lab build and operations work. The Windows coding squad (Claude Code, Codex, Antigravity) takes work through `LOUNGE-*` issues. Model APIs (MiMo, Meta, OpenAI, Baseten) never initiate contact; they are called through GitHub Actions event routes or directly by a resident agent.

Two environments were added around 2026-11-01–02. The cloud development environment **midorun** on OCI (built 2026-11-01) runs Claude Code, and Claude Code (CLI) is the development axis for both the cloud environment and the home lab (decided 2026-11-02); Anthropic access is API-based as the basic stance. The home lab gained a Mac mini (M4, arrived 2026-11-01) as an experiment host for multiple AIs, with **OpenClaw** (open-source, self-hosted) as its orchestration gateway. The lab-operations agent **Kurocchi** runs on OpenClaw (selected 2026-11-01) and starts read-only: monitoring → triage → approved procedures → verification. The owner's daily contact channel is LINE; lab-operations notifications go to Discord. Antigravity is used only through the official client on the owner's own devices and is not deployed into the OCI environment or OpenClaw (decided 2026-11-02, after public reports of account suspensions tied to third-party OAuth use).

The full diagram is below, reflecting the state as of 2026-11-02. The per-link inventory, cadences and verification status as of 2026-10-30 live in the [network topology snapshot](network-topology-2026-10-30.md) ([日本語](network-topology-2026-10-30.ja.md)).

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

Larger view of the current diagram (2026-11-02): [full-size PNG](../assets/network-topology-2026-11-02.png). The 2026-10-30 snapshot PNG is kept at [assets/network-topology-2026-10-30.png](../assets/network-topology-2026-10-30.png).

## Update — 2026-11-02

- **Home lab grows an orchestration layer.** A Mac mini (M4) arrived on 2026-11-01 as an experiment host for multiple AIs. OpenClaw (open-source, self-hosted) is adopted as its orchestration gateway, and the lab-operations agent Kurocchi — selected on 2026-11-01 over Hermes Agent — starts read-only: monitoring → triage → approved procedures → verification. Channels are split: LINE for the owner's daily contact, Discord for lab-operations notifications. Dots leads the home-lab build and operations work.
- **Development axis decided (2026-11-02).** Claude Code (CLI) is the axis for both the cloud development environment and the home lab. The OCI environment midorun (built 2026-11-01) runs Claude Code; Anthropic access is API-based as the basic stance.
- **Antigravity policy (2026-11-02).** Antigravity is used only through the official client on the owner's own devices; it is not deployed into the OCI environment or OpenClaw, after public reports of account suspensions tied to third-party OAuth use.
- **Roles confirmed.** Owner = PMO and final decisions; Fuwatchi (Muse) = direction, design, review and media; Dots = home-lab build and operations; coding execution = Claude Code / Codex and the connected APIs (Meta Model API, MiMo, OpenAI, Baseten, Modal).
- **Lounge cadence.** Fuwatchi's status share moved to every 2 hours on 2026-11-01; the mailbox watch stays every 30 minutes (06:00–22:00 JST).

