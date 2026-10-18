# Reusable Handoff Templates

[English](handoff-templates.md) | [日本語](handoff-templates.ja.md)

Use a short, bounded handoff when work crosses tools. Dottie coordinates PM, task scope, provider/environment selection, progress, and acceptance. AI Governance Control is the thin reusable handoff/artifact/evidence layer. AIteamBridge is a separate local capacity/router/transport project; live quota retrieval and automatic dispatch remain unverified.

Follow the current [roles and allocation procedure](operating-decisions-2026-10-13.md). Handoffs must focus on **diffs, artifact references (paths/SHA/diff), and structured summaries**; copying or resending full conversation histories is prohibited (do not mandate rigid N-turn windows; provide only the bounded context needed for the task).

Categorize and log failure causes:
- **Authorization Denial (`authorization`)**: Stop immediately (`fail-closed`). Retrying through alternate IDs, pathways, or unauthorized parameters is prohibited.
- **Environment Glitch (`environment`) / Timeout (`timeout`) / Quality Defect (`quality`)**: Preserve cause and artifacts after one failure, and consider at most one authorized candidate (max one fallback; no unauthorized runaway retries). If unavailable, mark `blocked` / awaiting owner handoff; do not automatically return to full-text Codex substitution.

## Template Selection Criteria

- **Concise 4-Item Progress Handoff**: Routine progress updates within the same environment, single-file edits, typo fixes, or bounded research summaries (low-risk tasks not crossing safety boundaries).
- **Evidence Manifest**: Cross-model / cross-provider escalations or handoffs, external service outputs, authentication/permission operations, approval gate transitions, logging handoff failures/exceptions, and multi-stage pipelines.

## Short progress handoff

Use these four fields for a routine status transfer. Point to the evidence manifest below when a claim needs detail; do not copy the entire conversation.

```text
purpose: [goal and observable completion condition]
current state: [proposed | accepted | executed | verified | blocked; name the environment]
evidence: [artifact path, revision, test result, or UNKNOWN]
next step: [one bounded action, owner, and any approval needed]
```

`accepted` means only that a request was received. `executed` needs an actual result artifact. `verified` needs a check against the completion condition on the stated revision. Do not promote an offline or mock result to live execution. A headless `request-review` authorization denial, including a soft denial, is `blocked`: preserve the rejection and ask for the authorized decision; do not retry through a different identity, permission, or route. Never place credentials, private conversations, or account-specific usage in a public handoff.

Offline examples (synthetic data only):

| Observation | Reported state | Next step |
|---|---|---|
| Worker accepted a request but returned no artifact | `accepted` | Read the result or preserve the timeout; no completion claim |
| Sample input produced an artifact and local checks passed | `verified (offline sample)` | Seek separately authorized live validation if required |
| Headless review was denied at the permission gate | `blocked` | Preserve the denial and request a specific authorized decision |

## Evidence manifest

For model comparisons or multi-stage work, freeze input artifacts, prompt, acceptance criteria, rubric, constraints, and evaluation procedure before execution.

```text
task_id:
goal / completion criteria:
small input / revision:
worker / one authorized alternative:
planned budget / work limit:
capacity pool / subscription quota observation (window, time, reset; unknown if unobserved) / api usage & charges (recorded only when available; not commingled with subscription units):
handoff failure / exception reason:
authorization stage / decision / evidence reference: unknown unless observed
input data class / approved destination: use public or synthetic data by default
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

## 7. PR Review Evidence

For the [PR Review Pipeline](pr-review-pipeline.md), record request acceptance separately from completion and verification.

```text
PR URL / base SHA / head SHA:
goal / acceptance criteria / changed files:
risk: low | medium | high | unknown; rationale:
builder tool / observed provider:
reviewer tool / observed provider / independence limitation:
requested review / completed review / reviewed SHA / result URL:
findings: ID / severity / file-line / evidence / impact / reproduction:
fix SHA / disposition / new-head review:
required checks / commands / result / current-head logs:
inapplicable gates / rationale / approved exceptions:
unresolved test and runtime gaps:
work limit / repair cycles / blocker:
merge authorization / human acceptance / decision / decision head SHA:
status: documented | configured | executed | verified
```

## 8. Limited final escalation to Claude Opus 5.5 Medium (2026-10-15)

Use only when a hard problem stalls under the owner-selected GPT/Sol worker: the same failure repeats, or no concrete progress within the agreed work limit. This is owner operating judgment, not a claim that Opus is objectively best. Follow the [2026-10-15 decision](operating-decisions-2026-10-15.md). Do not include secrets, private conversations, account identifiers or quota balances; use the smallest non-secret source/revision.

```markdown
# Goal and acceptance criteria
[Bounded target]

## Preserved state
- Phenomenon:
- Reproduction:
- Attempted methods and results:
- Unverified items:
- Constraints (permissions, TLS validation, secrets, paid-action approvals):
- Smallest non-secret source / revision:

## Delegation bounds
- Work limit (return to ordinary model at completion or limit):
- Token capacity / cost checked (unknown / stale if not evidenced):
- Requested model/effort: Claude Opus 5.5 Medium
- Observed runtime model/effort: UNKNOWN unless evidenced

## Rules
- Do not bypass a denial or silently change the runtime, model, TLS settings or permissions; stop and report instead.
- Report changed files, checks, current-revision evidence, unverified items and blockers.
```
