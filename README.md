# Multi-AI Workflow Architecture

[English](README.md) | [日本語](README.ja.md)

## 2026-11-09: One-week GPT-6.1 Sol / xhigh experiment

- **Period:** Monday, 2026-11-09 through Monday, 2026-11-16 (JST), followed by a review.
- **New work:** Use **GPT-6.1 Sol** (`gpt-6.1-sol`) with **Extra high** reasoning (`xhigh`) for new Codex and Dots-coordinated ChatGPT Work tasks during this period. Work already in flight may keep its current setup.
- **Usage goal:** Aim to use **at least 90%, as close to 100% as practical**, of the included weekly usage allowance by progressing useful, already-needed work. Track the percentage in the official usage dashboard rather than treating the allowance as a fixed raw-token count.
- **Workload boundary:** Do not invent extra tasks, repeat tests without a reason, or expand scope just to consume the allowance. Existing budgets, permissions and stop conditions still apply.
- **Review on 2026-11-16:** Compare completed work, quality, elapsed time and actual usage, then decide whether to continue or adjust the model choice.
- **Reset planning:** Plan use of two banked reset opportunities before they expire. Their expiry dates need confirmation in the official account UI; specific work allocation is still undecided.

[Official usage guidance](https://learn.chatgpt.com/docs/pricing) explains that Codex and ChatGPT Work share usage and directs users to their dashboard for current limits and reset times. A general November doubling of Pro's allowance has not been verified from the official sources checked on 2026-11-09. This section records the trial policy, not proof that every environment's model setting has already changed.

A high-level map of how several AI tools work as a team: Dots coordinates implementation, Muse (Fuwatchi) supports design and review, and Kurotchi handles lab-side work through OpenClaw. This page focuses on the current structure; older material is reachable from the [archive index](docs/archive/README.md).

## Previous update: 2026-11-08

- Simplified the overview around the current roles and logical architecture.
- Updated the diagram to include the Mac/OpenClaw lab, coding tools, browser and shared lounge.
- Moved the entry point for older updates and complete previous overviews to the archive index. Existing dated documents and historical diagrams remain available.

## Architecture at a glance

```mermaid
flowchart TB
    OWNER["Owner / decisions and acceptance"]
    DOTS["Dots<br/>coordination and implementation"]
    MUSE["Muse / Fuwatchi<br/>consultation, design and review"]
    LOUNGE["Private GitHub lounge<br/>asynchronous information sharing"]
    subgraph LAB["Mac lab"]
        KURO["Kurotchi / OpenClaw<br/>lab-side work"]
        CLI["Codex / Claude Code"]
        BROWSER["Dedicated browser"]
    end
    WORKERS["Task-specific coding tools<br/>Codex / Claude Code / official Antigravity"]
    API["On-demand model APIs"]
    OWNER --> DOTS
    OWNER --> MUSE
    OWNER --> KURO
    DOTS <--> LOUNGE
    MUSE <--> LOUNGE
    KURO <--> LOUNGE
    KURO --> CLI
    KURO --> BROWSER
    DOTS -.->|"select per task"| WORKERS
    DOTS -.-> API
    MUSE -.-> API
    KURO -.-> API
```

The arrows show logical responsibilities and information-sharing relationships, not physical routing or proof of continuous automatic operation. Dashed links are task-dependent choices. Coding tools and model APIs are invoked for a task; they are not additional resident team members. Antigravity refers to its official client.

## How work moves

1. The owner sets the goal and makes consequential decisions.
2. Dots coordinates the work and selects an appropriate implementation or research tool. Muse supports consultation, design and review; Kurotchi provides a lab-side entry point to CLI and browser work.
3. The private lounge provides asynchronous information sharing. A received message is information, not permission to execute it.
4. Results and review evidence return to the owner for acceptance. A logical connection does not mean every task or tool combination has been accepted end to end.

This public overview intentionally omits internal operating status, schedules, test transcripts, account details and security configuration. Updating the documentation does not change any runtime, permission or deployment.

## Read more

- [Detailed role map and source notes](docs/network-topology-2026-11-08.md)
- Guides: [AI team](docs/ai-team.md), [routing](docs/routing-guide.md), [handoffs](docs/handoff-templates.md), [review pipeline](docs/pr-review-pipeline.md)
- History: [archive index](docs/archive/README.md), [changelog](CHANGELOG.md)
- Reference: [tools](tools/README.md), [configuration guides](configs/), [templates](templates/), [tests](tests/), [diagram sources](tools/architecture/README.md)
