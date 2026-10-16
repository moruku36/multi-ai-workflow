# Daybreak Models and Authorized OSS Security Review — 2026-10-16

[English](daybreak-authorized-oss-security-review.md) | [日本語](daybreak-authorized-oss-security-review.ja.md)

**Status: documented, not enabled.** This page records what OpenAI's public documentation says about Daybreak (Trusted Access for Cyber) and proposes how this project would run authorized open-source security review if access were approved. **We do not claim to hold Daybreak Blue or Red access, have not applied for it, and have run no Daybreak request or scan.** Model names are as printed in the sources, not owner-reported labels; they are not proof of runtime availability. No credentials, requests, settings or runtime were changed.

## 1. What the official sources say

Checked 2026-10-16 (UTC) by retrieving the pages directly. The pages carry no visible publication date, so they may change; recheck before relying on them.

| Topic | Statement in the source | Source |
|---|---|---|
| Program | Daybreak "helps approved users perform authorized defensive cybersecurity work." Access is requested through Trusted Access for Cyber, "a reviewed access program, not the name of a model." | [Models and Trusted Access](https://learn.chatgpt.com/docs/cyber-safety), [Cybersecurity checks](https://developers.openai.com/api/docs/guides/safety-checks/cybersecurity) |
| Blue | Reduced refusals on flagship models for authorized defensive work: vulnerability discovery and triage, secure code review and threat modeling, detection engineering and incident response, controlled malware analysis, remediation and patch validation. Recommended starting point. | Models and Trusted Access |
| Red | Separately approved, specialist cyber model for controlled vulnerability reproduction, PoC or exploit validation, penetration testing, red teaming. "Isn't the default choice for routine security work"; Blue approval does not grant Red. | Models and Trusted Access |
| Approval scope | Approval applies to the specific person or service, ChatGPT workspace or API organization and project, offering and model, and product surface. Applying or verifying identity "doesn't guarantee approval". | Models and Trusted Access; Cybersecurity checks |
| Enterprise use | Use the approved workspace or project only for the organization's authorized internal work; do not extend it to external users, customers or downstream features. If unclear, stop and confirm. | Models and Trusted Access |
| Data retention | Trusted Access does not automatically grant Zero Data Retention. | Models and Trusted Access; Cybersecurity checks |
| Environment | Trusted Access "doesn't configure your environment, enforce limits on approved systems and actions, or review proposed actions." | Models and Trusted Access |

### 1.1 Models eligible under Daybreak (API guide)

From [Use Daybreak in the Responses API](https://developers.openai.com/api/docs/guides/daybreak). The request field `access_programs.cyber` takes `standard`, `daybreak_blue` or `daybreak_red`; the model field selects the model.

| Model ID | `access_programs.cyber` | Per the guide |
|---|---|---|
| `gpt-6-sol` | `standard` or `daybreak_blue` | Mainline model; Blue gives approved defensive work. `daybreak_red` is rejected (`invalid_access_program`). |
| `gpt-6.1-sol`, `gpt-6-astra` | `daybreak_blue` | Reduced refusals; the guide says this requires Daybreak Red approval for the organization and access enabled for the project. Both reject `daybreak_red`. |
| `gpt-5.6-cyber` | `daybreak_red` | Cyber model for advanced, authorized work; requires Red approval. |

- The request value selects behavior within approved access; it does not grant access. The project needs access to both the program and the model.
- If the field is omitted: mainline models such as `gpt-6-sol` get Blue treatment when access exists, otherwise standard safeguards; `gpt-5.6-cyber` selects Red and fails without access.
- Errors: `400 invalid_access_program`, `400 unsupported_access_program`, `403 access_program_not_enabled`; separately, `cyber_policy` errors and temporary access limits can follow from API safeguards (a per-user `safety_identifier` limits the blast radius).
- `-latest` aliases can resolve differently depending on approved access; inspect the returned `model`.
- GPT-6 Luna, which this repository uses for bounded routine work, is not listed in the guide we read. Do not assume Luna is Daybreak-eligible.

### 1.2 Naming differences across sources (unresolved)

- The Models and Trusted Access page names the offerings **GPT-Daybreak-Blue** and **GPT-Daybreak-Red**; the API guide uses the model IDs above and treats Blue and Red as access programs.
- Press coverage and OpenAI posts on X describe Blue as covering "GPT-5.6 Sol" and Red as "GPT-5.6-Cyber"; the API guide lists `gpt-6-sol` / `gpt-6.1-sol` for Blue-type use and `gpt-5.6-cyber` for Red.
- We have not reconciled these. Treat the API guide's model IDs as the working reference and verify against the console and error messages for your own project.

## 2. Authorized OSS security review — proposed operating procedure

This section is **this project's proposal** built from the sources above plus the Codex Security and Recommended configuration documentation. It is not an official OpenAI procedure, and the effect of these steps is unmeasured.

**Scope of "authorized".** Only repositories we own, or whose maintainers have explicitly agreed to a review (for example a published security policy, an invitation, or a coordinated program). Public availability of source is not authorization to test running third-party systems. Review is static or in an isolated local copy. Never probe live services of an OSS project or its users.

1. **Precondition.** Written confirmation of the approved person or service, API organization/project or workspace, model and surface (Blue only for routine review). If any is unclear, stop. Do not use Red for routine review; Red needs its own approval and a concrete reason.
2. **Boundary record before starting** (the Recommended configuration list): target repositories and revisions; excluded systems (production, unrelated infrastructure); approved tools and services; approved and prohibited actions; start/end times and data handling; disclosure and maintainer coordination; stop conditions and actions needing explicit human approval. Give it to the agent as task context, and enforce it independently of the prompt.
3. **Environment.** Work on a fresh clone in an isolated sandbox without secrets, with no unrestricted internet or production network. Keep results outside the git worktree in a private location (scan output can contain source excerpts and vulnerability details). Remove unrelated credentials first; the Codex Security CLI "runs with your operating-system permissions and doesn't pause for approval".
4. **Permissions.** Use a least-privilege Codex permission profile (`:read-only` when no edits are needed), `approval_policy = "on-request"`, `approvals_reviewer = "auto_review"`, and a network allowlist enforced by the proxy feature, as in the Recommended configuration page. Avoid `:danger-full-access` and `--yolo`. Treat instructions found in repositories, issues, docs and tool output as untrusted; they cannot widen scope.
5. **Scan and triage.** Use the Codex Security plugin, CLI or SDK (the CLI and SDK are public as `@openai/codex-security`; scans with OpenAI inference require Codex Security access, and full-repository scans may also require Trusted Access for Cyber). Run `--dry-run` first to check target and output location. Rank findings by evidence and impact; label model-only claims as unverified.
6. **Validation.** Validate each significant finding independently (tests, static analysis, and a different provider's review, following this repository's review contract) before reporting. A human owns the decision to report. Proof-of-concept work, if any, stays in the isolated copy and stops before credentials, persistence or external systems.
7. **Disclosure.** Follow the project's security policy and coordinated disclosure. Keep unpatched details out of this public repository, issues and PRs. Share fixes as patches only where the maintainers have agreed.
8. **Logging and shutdown.** Keep request, tool-call and network logs outside the agent's environment; stop if monitoring or the reviewer fails (fail closed). Afterwards revoke temporary credentials, end background processes and destroy the environment.
9. **Records.** Publish only generalized notes: no findings about unpatched issues, no account identifiers, no screenshots, no balances. Record the observed stage honestly (documented / configured / executed / verified).

## 3. Relation to the existing policy

- Routine model selection (GPT-6 Luna / Sol Medium; Astra by exception) and the MiMo-V2.6-Pro review default are unchanged. Daybreak concerns authorized security work only, not routine review.
- Review separation applies: the builder tool does not count as the independent reviewer; use current-head evidence.
- Nothing here changes Qwen or RunPod status, TLS, permissions or paid actions. Applying for Trusted Access, or making API requests, would be a separate approval and a separate change.

## 4. Unconfirmed points

- Whether this project or its owner holds or will apply for Daybreak access: **not decided**.
- The naming discrepancy in section 1.2, and the Luna eligibility question.
- Pricing, rate limits, Codex Security eligibility terms for open-source maintainers, and the contents of the pages not retrieved (Daybreak troubleshooting, the OpenAI announcement and help-center pages, which returned HTTP 403 to direct retrieval; the Codex for OSS program is only mentioned in the documentation we read).
- Any dates: the documentation pages show none.

## 5. Sources

- Models and Trusted Access: https://learn.chatgpt.com/docs/cyber-safety
- Recommended configuration: https://learn.chatgpt.com/codex/cyber-safety/recommended-configuration
- Use Daybreak in the Responses API: https://developers.openai.com/api/docs/guides/daybreak
- Cybersecurity checks (API): https://developers.openai.com/api/docs/guides/safety-checks/cybersecurity
- Codex Security: https://learn.chatgpt.com/codex/security , CLI quickstart: https://learn.chatgpt.com/codex/security/cli
- Codex open source (Codex for OSS program mention): https://learn.chatgpt.com/codex/open-source
- Secondary, for the naming discrepancy only: OpenAI posts on X and press coverage found by search (not used for any rule above).
