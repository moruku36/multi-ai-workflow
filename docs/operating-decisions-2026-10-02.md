# AI team operating decisions — 2026-10-02

[English](operating-decisions-2026-10-02.md) | [日本語](operating-decisions-2026-10-02.ja.md)

This dated record updates the operating policy. CLI observations below were reported in the owner's operating session; they were not rerun for this documentation change. Approval of a direction, acceptance of a command, execution, and verification are separate facts.

## Roles and model selection

| Role | Responsibility |
|---|---|
| Dottie | PM/orchestrator: scope, assignment, handoffs, quota awareness, and evidence tracking |
| Chappy | Architect and independent reviewer; OpenAI research, writing, and explicitly assigned Codex work remain available |
| Claude | Default coding and deployment engineer, using Sonnet; deployment still requires the applicable authorization |
| Gemini / Antigravity | PoCs, mocks, and initial implementations, then hand off the same artifact to Claude |
| Qwen | Multimodal work and research; local text and Colab capabilities remain distinct |

Ordinary **Codex** writing/coding starts at Luna / Low, escalating only when needed through Luna Medium, Luna High, then Sol Medium as already documented. This is a model policy for Codex work, not a requirement to route all coding to Codex. Preserve explicit user assignments and reuse existing implementations.

For **distillation and Factory**, the owner expressly permits **Astra for initial research and paper interpretation**. Use efficient Sol when sufficient. This exception does not make Astra the default for every task or replace the ordinary coding escalation policy. Claude defaults to Sonnet; Opus remains for hard work. Existing versioned model labels are owner-reported snapshots, not proof of the runtime model or new API identifiers.

The existing optional Astra path for difficult tasks remains available within previously authorized scope when Sol is insufficient and the need is judged individually. It is separate from the ordinary Codex escalation ladder and never an automatic next step. The research exception neither prohibits those prior uses nor authorizes Astra for every task.

**Gemini effort discrepancy:** the prior repository policy says High normally, with Medium when quota is low after considering reset time and difficulty. The owner's current preference is Medium. Record this preference for the current work and retain the discrepancy explicitly; do not silently redefine every Gemini task as Medium or treat the prior High rule as the owner's current choice. Log the requested effort per task and the observed runtime separately.

## Comparison and evidence contract

Before comparing models, freeze the same input artifacts, prompt, acceptance criteria, rubric, constraints, and evaluation procedure. Create an artifact manifest before any comparison run. Record changes as a new comparison rather than pooling unlike runs.

Minimum manifest fields:

```text
task_id / comparison_id:
input_revision / paths / content_hashes:
prompt_revision / rubric_revision / acceptance_criteria:
provider / route / CLI_version / environment:
requested_model / requested_effort:
observed_runtime_model / observed_runtime_effort: UNKNOWN unless evidenced
accepted: status / receipt_reference
executed: status / run_reference
verified: status / check_reference
output_paths / content_hashes:
review_findings / verification_results / unresolved_items:
reacquire_source / revision_or_hash:
```

Requested model/effort is not proven runtime model/effort. Use `UNKNOWN` when runtime evidence is unavailable; never infer an identifier from a role, alias, request, or OK response. Keep `accepted`, `executed`, and `verified` separate. A queue receipt establishes acceptance only; read the result and verify acceptance criteria before reporting completion. Publish only sanitized manifests and evidence references, never private session contents.

## Reported CLI verification boundaries

| Route | Reported evidence | Still unverified |
|---|---|---|
| Claude, Mac existing cloud session | Actual CLI send verified | This does not prove the Windows route |
| Claude, Windows 2.1.287 | Syntax supported; local Sonnet no-tool OK test passed | Actual send to an existing cloud session on Windows has not been exercised; a queue receipt is not a result read |
| Antigravity, Windows 1.2.14 | No-tool OK test with requested `gemini-3.8-flash-medium` passed; headless JSON, timeout, and conversation capabilities available | No equivalent cloud-session route confirmed; the request label alone does not prove the runtime model or coding/tool execution |

These narrow tests do not establish deployment, repository edits, unattended execution, or full automatic integration. No additional paid/model runs are required for this documentation update.

## Windows base and Factory next steps

Windows is the intended always-on local base. **Reported status as of 2026-10-02:** the Windows wrapper (task7) prototype is implemented with **14 offline tests passed**, but live execution through the wrapper has **not been tested**. The Antigravity wrapper is blocked pending verification of supported per-invocation tool-scope controls. This is a dated implementation/verification status, not a general product limitation. These observations were reported from the owner's operating session and were not rerun for this documentation update. Dottie's cloud PM role, CodexBar routing, and local agent adapters remain subject to the previously documented integration checks; do not claim a fully automated workflow.

The **Factory minimal manifest / review / reacquire direction is approved for implementation**, but has not been proven. Start with the manifest contract above, review artifacts and findings against the frozen rubric, and retain source/revision/hash references to reacquire inputs and outputs. Missing artifacts require reacquisition and re-verification, not reconstruction from memory. Keep implementation approval distinct from successful implementation and end-to-end verification.

## Public documentation boundary

Exclude secrets, authentication data, personal health information, corporate mail, and private notes. This update authorizes documentation work only: no installs, security/authentication/settings changes, paid usage, or automatic deployment. Report the local diff and checks before push, PR creation, or merge.
