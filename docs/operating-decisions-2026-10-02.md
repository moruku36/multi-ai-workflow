# AI Team Operating Decisions — 2026-10-02

[English](operating-decisions-2026-10-02.md) | [日本語](operating-decisions-2026-10-02.ja.md)

> **Legacy (dated record):** Model selection is superseded by the [2026-10-06 owner policy](operating-decisions-2026-10-06.md). The historical ladder, experiments, and observations below are retained as history, not current recommendations.

This dated record captures operating policy as of 2026-10-02. CLI observations were reported from the owner's session at that time and were not rerun for this documentation update. Approval of a direction, command acceptance, execution, and verification are separate facts. The [2026-10-05 later policy](operating-decisions-2026-10-05.md) updates later routing choices.

## Roles and model selection

| Role | Responsibility |
|---|---|
| Dottie | PM/orchestrator: scope, assignment, handoffs, quota awareness, and evidence tracking |
| Chappy | Architect/independent reviewer; OpenAI research, writing, and explicitly assigned Codex work |
| Claude | Coding/deployment engineer in the snapshot; Sonnet as usual, with applicable authorization for deployment |
| Gemini / Antigravity | PoCs, mocks, and initial implementations, with the documented handoff of the same artifact to Claude |
| Qwen | Multimodal work; distinguish local text environment from Colab capabilities |

The ordinary Codex writing/coding path at that time started at Luna / Low and could escalate through Luna Medium, Luna High, then Sol Medium. This applied to Codex work, not all coding. Preserve explicit owner assignments and reuse existing implementations.

For distillation and Factory initial research, the owner expressly permitted Astra for paper interpretation; use Sol when sufficient. This exception did not make Astra the default for all tasks. Claude used Sonnet as the normal model and Opus for hard work. Versioned model labels are owner-reported snapshots, not proof of runtime identity or API identifiers.

The historical Gemini effort policy and the owner's preference differed at this snapshot: the repository described High normally and Medium when quota was low after considering reset and difficulty, while the owner preferred Medium for that work. This dated record is superseded for current routing by the 2026-10-05 task-based policy; requested effort and observed runtime should be recorded separately.

## Comparison and evidence contract

Before comparing models, freeze the same input artifacts, prompt, acceptance criteria, rubric, constraints, and evaluation process. Create a manifest before a comparison run. Record changed conditions as a separate comparison.

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

Requested model/effort does not prove the runtime model/effort. Use `UNKNOWN` when evidence is missing. Keep `accepted`, `executed`, and `verified` separate; a queue receipt establishes acceptance only. Read outputs and verify acceptance criteria before reporting completion. Publish sanitized manifests and evidence references only.

## CLI verification reported at the time

| Route | Reported evidence | Not established by that evidence |
|---|---|---|
| Claude, existing Mac cloud session | Actual CLI send verified | Windows route |
| Claude, Windows 2.1.287 | Syntax supported; local Sonnet no-tool OK test passed | Actual send to an existing Windows cloud session; a queue receipt is not a read result |
| Antigravity, Windows 1.2.14 | No-tool OK test using requested label `gemini-3.8-flash-medium`; headless JSON, timeout, conversation capabilities | Cloud-session equivalence, runtime identity from the request label, coding/tool execution |

These narrow tests did not establish deployment, repository edits, unattended execution, or full automation.

## Windows base and Factory at the time

Windows was the intended always-on local base. As reported on 2026-10-02, the Windows wrapper prototype (task7) had 14 offline tests passed, but live execution through it was untested. The Antigravity wrapper was pending verification of per-invocation tool-scope controls. These were dated observations, not general product limitations. Dottie's cloud PM role, CodexBar routing, and local-agent adapters still required integration verification; the workflow was not described as fully automated.

At that time, the Factory minimal manifest/review/reacquire direction was approved for implementation but unproven. Preserve source/revision/hash references for reacquiring artifacts; missing artifacts require reacquisition and re-verification, not reconstruction from memory. Keep implementation approval distinct from end-to-end verification. See the 2026-10-05 record for later Factory evidence.

## Public documentation boundary

Exclude secrets, authentication data, personal information, corporate mail, and private notes. This documentation work did not authorize installs, security/authentication/settings changes, paid usage, or automatic deployment.
