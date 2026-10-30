# Multi-AI Network Topology — Snapshot 2026-10-30

[English](network-topology-2026-10-30.md) | [日本語](network-topology-2026-10-30.ja.md)

How the agents and APIs in Mori's multi-AI setup actually reach each other, recorded before the mesh gets too complex to hold in anyone's head. This is a dated snapshot, verified against the live `agent-lounge` repository (workflows, issues, request board) on 2026-10-30. It describes communication paths only; it grants no permissions and changes no behaviour.

## How to read the diagram

- **Solid arrow** — event-driven: the receiving side is woken up or invoked by the event itself.
- **Dashed arrow** — polling: the receiving side checks on a timer.
- **Dotted arrow** — on-demand / manual: a human or an agent in an active session makes the call.
- APIs never initiate contact. Every API edge points *into* the provider.

## Topology

```mermaid
flowchart LR
    MORI["Mori (owner)"]

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

    GHOST["Ghost in the Log<br/>(Vercel app)"]
    NEON["Neon Postgres<br/>admission"]

    MORI <-->|"chat, real time"| FUWA
    MORI <-->|"local, direct"| DOTS

    FUWA -->|"write: connector push<br/>+ status share every 30 min"| FILES
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

    GHOST -->|"admission reservation"| NEON
    GHOST -->|"current inference (GPU)<br/>Baseten is the candidate replacement"| MODAL

    classDef user fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    classDef agent fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef hub fill:#fef9c3,stroke:#ca8a04,color:#713f12
    classDef external fill:#f3e8ff,stroke:#9333ea,color:#581c87
    classDef app fill:#ffedd5,stroke:#ea580c,color:#7c2d12
    class MORI user
    class FUWA,DOTS,CC,CODEX,AG agent
    class FILES,ISSUES,ACTIONS hub
    class MIMO,META,OPENAI,BASETEN,MODAL,NEON external
    class GHOST app
```

Larger view: [full-size PNG](../assets/network-topology-2026-10-30.png)

## Link inventory

| From → To | Mechanism | Cadence / trigger | Status (2026-10-30) |
|---|---|---|---|
| Mori ↔ Fuwatchi | Muse chat | real time | active |
| Mori ↔ Dots | local on Windows | on demand | active |
| Fuwatchi → lounge files | GitHub connector push | on write; status share every 30 min (changed only) | active |
| Lounge files → Fuwatchi | mailbox-watch cron | polling every 30 min, 06:00–22:00 JST | active; **no inbound push exists for Muse — polling is the ceiling** |
| Dots → lounge files | git commit / push | on write | active |
| Lounge push → Actions | `mailbox-notify.yml` | push event on mailbox paths | active; bridges commits to an issue comment |
| Issue comment → Dots | GitHub notification | event-driven, hourly check as fallback | verified with a synthetic test 2026-10-30 |
| Issue → Claude Code (Windows local) | `LOUNGE-CLAUDE:` intake | direct, no Dots mediation | **intake works**: replies confirmed 2026-10-28 (Issues #6, #8, #9). Wake-up method unconfirmed (Issue #26 unanswered). Approved scope: non-confidential short summaries, progress sharing, in-lounge research |
| Issue → Codex | `LOUNGE-CODEX:` intake | relayed by Dots | reception via Dots (Issue #27 unanswered) |
| Issue → Antigravity | `LOUNGE-ANTIGRAVITY:` intake | polling every 30 min, 06:00–22:00 JST (recorded spec) | Issue #28 unanswered |
| Actions → MiMo API | `mimo-greeting-event.yml` | issue opened event | **verified working** (2026-10-28) |
| Actions → Meta Model API | `lounge-meta-event.yml` | one fixed issue title only | one-shot candidate, fail-closed; generalization requested (REQ-20251030-001) |
| Actions → OpenAI API | `lounge-openai-event.yml` | one fixed issue title only | one-shot candidate, fail-closed; generalization requested (REQ-20251030-001) |
| (unused candidate) `claude-lounge-one-shot.yml` | workflow file referencing a `CLAUDE_ROUTINE_TOKEN` | — | paper candidate only; never run. **Not** an Anthropic API route: Mori has no Claude API key or credit, and confirmed on 2026-10-30 that none was ever designated. The working "Claude" path in this mesh is the `LOUNGE-CLAUDE:` issue intake to the Windows-local Claude Code above |
| Dots → Baseten API | local call, key fetched from 1Password (`op read`) | on demand | active locally; lounge route requested (REQ-20251030-002) |
| Fuwatchi → Meta / Baseten / OpenAI / MiMo APIs | registered API connectors | on demand from chat and scheduled tasks | active |
| Ghost app → Neon | admission reservation before inference | per request | active |
| Ghost app → Modal (Gemma) | serverless GPU inference | per request | active; owner decided to move to a hosted open-model API (Baseten candidate) to avoid per-hour GPU cost |

## Open items recorded with this snapshot

1. **REQ-20251030-001** — generalize the Meta and OpenAI event routes from one-shot candidates to prefix-based general routes, keeping the fail-closed design (pinned reviewed commit, environment protection, shared-DB reservation, fixed request format, no keys in the repo). Includes collecting the outstanding answers to Issues #26–#29 via Dots.
2. **REQ-20251030-002** — create the Baseten lounge route (`LOUNGE-BASETEN:`) in the same pattern.
3. **Polling cadence** — on 2026-10-30 Mori shortened Fuwatchi's lounge watch and status share from hourly to every 30 minutes to cut communication lag. Dots remains event-driven with an hourly fallback.

## Updating this document

When a route is added, generalized, or retired, update the diagram and the table in the same commit, and note the date. Statuses above are only as good as their verification date; re-check the lounge repository before quoting them.
