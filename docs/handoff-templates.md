# Reusable Handoff Templates

[English](handoff-templates.md) | [日本語](handoff-templates.ja.md)

Use a short, bounded handoff when work crosses tools. Dottie coordinates PM, task scope, provider/environment selection, progress, and acceptance. Factory is the thin reusable handoff/artifact/evidence layer. AIteamBridge is a separate local capacity/router/transport project; live quota retrieval and automatic dispatch remain unverified.

Follow the current [roles and allocation procedure](operating-decisions-2026-10-10.md). Preserve the cause after one ordinary failed handoff and consider one other authorized candidate. Stop on authorization denial without bypassing it. If unavailable, mark `blocked` / awaiting owner handoff; do not automatically return to full-text Codex substitution.

## Evidence manifest

For model comparisons or multi-stage work, freeze input artifacts, prompt, acceptance criteria, rubric, constraints, and evaluation procedure before execution.

```text
task_id:
goal / completion criteria:
small input / revision:
worker / one authorized alternative:
planned budget / work limit:
capacity pool / session-weekly observation time / reset time: unknown unless evidenced
handoff failure / exception reason:
input revision / paths / hashes:
prompt / rubric / acceptance criteria:
provider / route / environment:
requested model / effort:
observed runtime model / effort: UNKNOWN unless evidenced
accepted / executed / verified: separate state and evidence reference for each
output paths / hashes:
review findings / test results / unresolved items:
reacquire source / revision / hash:
```

A request shown as accepted or Working is not proof of completed work. Read the result and verify acceptance criteria. A local/offline test does not prove a live provider path or production change.

## 1. Product Owner / Dottie to a production, research or implementation worker

```markdown
# Goal
[Desired outcome]

## Scope and constraints
- In scope:
- Out of scope:
- Environment / provider constraints:

## Acceptance criteria
- [Observable result]

## Requested model/effort (if any)
[Task-specific choice; do not generalize it]

## Report back
- Changed files / artifacts:
- Checks run and results:
- Accepted / executed / verified status:
- Unknowns and blockers:
```

## 2. Qwen research handoff

```markdown
# Research question
[Question]

## Inputs and permitted sources
- Files / URLs:
- Read-only or other boundary:

## Findings
- Finding with source/page/region:
- Confidence or ambiguity:

## Handoff
- Evidence/artifact references:
- Questions for the next tool:
- Do not infer implementation, runtime success, or permission from research output.
```

## 3. Optional PoC to production refinement

Only use this route when a PoC reduces meaningful uncertainty. Preserve the existing artifact; avoid duplicate initial implementations.

```markdown
# Goal and acceptance criteria
[Bounded target]

## Existing artifact and verification
- Revision / files:
- Tests already run:
- Known gaps:

## Refinement request
- Preserve working behavior and architecture unless evidence supports a change.
- Report edits, checks, unresolved issues, and any required approval.
```

## 4. Independent review

```markdown
# Review request
Review the supplied revision independently. Do not implement changes.

## Scope
[Files / change / risk areas]

## Output
- Critical/Major findings with file/line, evidence, impact, and reproduction/check:
- Unverified assumptions:
- Important test gaps:
- If none, state that and list remaining runtime limitations.
```

## 5. Apply verified review findings

```markdown
Apply only these confirmed findings:
[Finding IDs and evidence]

Keep changes minimal. Run relevant checks. Report changed files, test results, and remaining unknowns.
```

## 6. Stop and preserve on authorization failure

```markdown
The required action was rejected at [authorization stage]. Do not retry repeatedly or use an alternate route to bypass it.
Preserve current work and report the exact action, target, rejection reason, saved artifacts, and authorized next step.
```
