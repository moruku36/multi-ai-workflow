# Local Efficiency Improvement Proposal Based on MiMo Review — 2026-10-19

[English](2026-10-19-mimo-efficiency-review.md) | [Japanese](2026-10-19-mimo-efficiency-review.ja.md)

- Record Date: 2026-10-19 (Asia/Tokyo)
- Fixed Target Commit: `92b135f168be897f22c699b177d4e9a789bccae6` (`origin/main`)
- Working Branch: `local/mimo-efficiency-review` (Dedicated local branch, creating local commit; no push, PR, or merge)
- Review Input: MiMo V2.6 Pro Review (base `mimo-v2.6-pro`, Knowledge Base / Chat History / Notes OFF, single-turn review based on public summary)
- Nature: Local improvement proposals and measurement design cross-referenced with public repository records. Based on this proposal, all adopted P0 items (#1, #3, #5, #8) and select P1 items (#2, #4) have been integrated locally into operational documents (`README.md`, `docs/handoff-templates.*`, `docs/routing-guide.*`, `docs/pr-review-pipeline.*`) as minimal bounded diffs. Unimplemented P1 items (#6, #7) and the measurement framework remain exploratory design proposals for future validation, with hypotheses separated from empirical claims.

---

## 1. Repository Facts vs. Hypotheses

This proposal strictly separates recorded objective repository facts from proposals, inferences, and unverified hypotheses.

### Verified Repository Facts
1. **Target Commit and Working Tree State**:
   - `92b135f168be897f22c699b177d4e9a789bccae6` is the base HEAD on `origin/main`.
   - The working tree was verified clean prior to editing; local modifications and subsequent commit are isolated on dedicated branch `local/mimo-efficiency-review`.
2. **Established Policies**:
   - `docs/routing-guide.md` / `configs/level2-antigravity/AGY_RULES.md`: Flash-centric operation, on-demand escalation to higher-tier models, and strict separation between operational labels and actual runtime (`UNKNOWN` when unproven) are already codified.
   - `docs/handoff-templates.md`: Concise handoff (4 items) and prohibition of replicating full conversation history are codified. Saving context upon failure, trying at most one alternative, and stopping immediately on authorization denial are established.
   - `docs/dots-codexbar-orchestration.md`: CodexBar quota images are checked manually; automated live quota retrieval and automated routing remain unverified.
   - `docs/pr-review-pipeline.md`: Binding to head SHA, distinct provider independent review, CI verification, and human (Product Owner) acceptance are mandatory quality gates.
   - `tools/pipeline.py`: Explicitly marked as a legacy auxiliary script and not the active primary workflow pipeline.

### Hypotheses and Unverified Items
1. **Unprovided / Unverified Empirical Logs**: Personal empirical baseline logs for token consumption, actual API billing, prompt cache hit rates, or retry counts were not provided or verified in this task; their absence outside the repository is not asserted.
2. **Non-guaranteed Outcomes**: Projected token reduction ratios and effort savings resulting from context minimization or static deterministic processing are hypotheses, not guaranteed metrics.
3. **Unverified Automations**: Automated quota retrieval, automated dispatch, and automated merge remain unverified and are not introduced in this proposal.

---

## 2. MiMo 8 Findings: Disposition and Priority Table

> **Note**: Regarding implementation status in this table: All adopted P0 items (#1, #3, #5, #8) along with P1 items #2 (template selection criteria) and #4 (tiered review depth) have been integrated into operational documents via this task. Conversely, P1 items #6 (event-driven quota observation) and #7 (deterministic static pre-checks and prompt cache evaluation), as well as the Section 5 measurement framework, remain exploratory proposals pending future validation (unimplemented).

| # | Target Document / Area | MiMo Finding Summary | Proposal Disposition | Proposal Priority | Implementation Status | Rationale and Action Plan |
|---|---|---|:---:|:---:|:---:|---|
| 1 | `docs/handoff-templates.md` | 4-item template and omitting full conversation confirmed. Resend context limit is unclear from excerpt. Proposes diff/summary/reference focus without mandating fixed N turns. | **Adopted** | **P0** | **Adopted & Integrated** | Resending full conversation history wastes tokens and risks credential leakage. Maintain focus on diffs, summaries, and artifact references (paths/SHA). Do not mandate fixed N turns, as rigid turn windows can break necessary context or include unneeded tokens. |
| 2 | `docs/handoff-templates.md` | Criteria for choosing between concise 4-item handoff and detailed manifest unclear. Proposes expanding fields on approval, external output, safety boundaries, multi-provider handoff, or retries without dropping required evidence. | **Adopted** | **P1** | **Adopted & Integrated** | Retain concise 4-item handoff for routine progress. Codify criteria requiring the detailed evidence manifest (or phased field expansion) specifically when crossing safety boundaries, producing external outputs, coordinating across providers, passing approval gates, or handling handoff failures. Retain all mandatory evidence fields (revision, capacity pool, requested/observed model, etc.). |
| 3 | `README.md`, `docs/routing-guide.md`, `AGY_RULES.md` | Flash-centric / on-demand escalation and distinction between labels and runtime confirmed. Proposes event-driven definitions for stagnation/blockers and demotion conditions, maintaining requested/observed/unknown separation. | **Adopted** | **P0** | **Adopted & Integrated** | Formally define escalation events (repeated failures, reaching agreed attempt limits) and demotion events (blocker resolved, transitioning to routine phase, or reaching upper budget limits to return to base model). Maintain strict logging of requested vs. observed runtime vs. unknown. |
| 4 | `docs/pr-review-pipeline.md` | Head SHA, distinct provider, CI, and human acceptance confirmed. Proposes differentiating review depth for routine docs vs. governance/safety docs to prevent duplicate reviews for the same objective. Avoid fixing MiMo as sole reviewer for all reviews. | **Partially Adopted** | **P1** | **Partially Adopted & Integrated** | **[Adopted]** Establish distinct review tiers for routine documentation (typos, minor markdown formatting) vs. governance/security/safety documentation to eliminate redundant reviews with identical scope.<br>**[Constraint / Rejected]** Reject designating MiMo as a universal reviewer across all types. Maintain the distinct provider principle and human final acceptance. |
| 5 | `docs/handoff-templates.md`, `docs/routing-guide.md` | Preservation after single failure, fallback to one authorized alternative, and stopping on denial confirmed. Proposes categorizing failure causes and codifying budget and retry limits. MiMo proposed fixed 2 retries (1 same + 1 alt), but check consistency with existing rules and avoid fixing numbers without empirical data. Stop immediately on denial. | **Partially Adopted** | **P0** | **Partially Adopted & Integrated** | **[Adopted]** Adopt taxonomy for failure causes (environment, authorization, timeout, quality), pre-set budget/work limits, and immediate fail-closed stop on denial.<br>**[Constraint / Modified]** Reject MiMo's fixed 2-retry proposal primarily for consistency with existing rules (save context after ordinary failure and consider at most 1 authorized alternative; max 1 fallback). Do not increase retry counts without authorization. Supplement: on authorization denial or security boundary violation, execution always halts immediately (fail-closed). |
| 6 | `docs/dots-codexbar-orchestration.md` | CodexBar images checked manually; live auto-retrieval/router unverified. Proposes observing only during events (task start, escalation decisions), treating stale data as unknown/manual, and deferring automated periodic polling. | **Adopted** | **P1** | **Adopted Proposal / Pending Validation** | Automated periodic background polling is deferred (rejected) due to token/API overhead and false-reading risks. Restrict quota observation to trigger events (task initiation, model escalation). Treat stale or missing readings as `unknown` and fall back to manual verification. |
| 7 | `tools/pipeline.py` | Legacy chain (Ollama format -> Claude API review) is not active workflow. Proposes executing deterministic checks (SHA match, links/whitespace, manifest validation) deterministically, using LLMs only where judgment is needed. Evaluate caching as hypothesis where static prefix exists and provider/confidentiality requirements are met, measuring hit rate. Do not modify legacy script. | **Partially Adopted** | **P1** | **Partially Adopted Proposal / Pending Validation** | **[Adopted]** Run deterministic checks (SHA verification, link integrity, trailing whitespace, manifest syntax) via deterministic scripts instead of LLMs. Evaluate prompt caching as a hypothesis where static prefixes exist, provider supports it, and confidentiality rules permit, measuring hit rate.<br>**[Constraint]** Keep `tools/pipeline.py` unmodified as legacy. Do not claim cache savings as established fact. |
| 8 | General Workflow / Concurrency and Exit Gates | Concurrency preference is at most 2 independent tasks; avoid confusing with repository-implemented auto-dispatch. Maintain head SHA match, required checks, resolution of blocking findings, and human acceptance. | **Adopted** | **P0** | **Adopted & Integrated** | Clarify that max 2 concurrent tasks is an operational capacity limit under manual oversight, not an automated dispatch feature in the repo. Maintain exit criteria: strict head SHA match, passing CI/static checks, resolution of blocker/major findings, and human (Product Owner) acceptance. |

---

## 3. Rejected or Deferred Proposals and Rationale

The following proposals are explicitly rejected or deferred to safeguard security, reliability, and auditability:

1. **Resending Full Conversation History (Rejected)**:
   - *Rationale*: Causes exponential token expansion and context exhaustion. Increases the risk of leaking internal trial-and-error logs or credentials to external providers. Replaced with diffs, artifact references, and structured summaries.
2. **Unverified Live Quota Auto-dispatch and Periodic Polling (Deferred / Rejected)**:
   - *Rationale*: Live quota APIs and automated screenshot parsing remain unverified. Relying on them risks erroneous routing or sudden task aborts. Periodic background polling also wastes API calls.
3. **Automated Approval and Automated Merge (Rejected)**:
   - *Rationale*: Human oversight (Product Owner acceptance) is required at safety boundaries, privilege levels, and production integrations to maintain organizational governance.
4. **Permanent Adoption of Legacy Chain (`tools/pipeline.py`) (Rejected)**:
   - *Rationale*: The script represents legacy tooling for prior local setups, not the active workflow. It must not be activated or substituted into production without formal review.
5. **Billing Estimates Assuming Operational Label Equals Runtime ID (Rejected)**:
   - *Rationale*: Operational designations (e.g., model labels) do not prove runtime CLI identifiers or actual billing tiers. Estimating costs on assumptions causes misleading metrics; `requested` and `observed runtime` must remain decoupled.
6. **Reduction or Bypassing of Quality Gates (Rejected)**:
   - *Rationale*: Omitting CI runs, regression tests, or distinct-provider reviews in the interest of speed or token savings directly compromises code quality.
7. **MiMo Proposals of Rigid N-Turns, Fixed 2-Retries, and Defining Task as Exactly 1 Head SHA (Rejected)**:
   - *Rationale*:
     - *Fixed N-Turns*: Rigid windowing truncates critical context or carries unneeded baggage depending on task characteristics.
     - *Fixed 2-Retries*: Rejected primarily for consistency with existing rules ("save context after ordinary failure and consider at most 1 authorized alternative; max 1 fallback"). Increasing retry attempts without authorization is prohibited. In addition, on authorization denial or security boundary violations, execution always halts immediately (fail-closed).
     - *Task = Head SHA*: Non-code tasks (exploratory research, architectural discussions) do not immediately produce commits.

---

## 4. Detailed Local Improvement Plan (By Proposal Priority and Implementation Status)

### Proposal Priority P0: Mandatory, Safety, and Fundamental Gates (Adopted & Integrated into Operational Docs)

#### 4.1 Context Minimization Principles (`docs/handoff-templates.md`) [Adopted & Integrated]
- Handoffs must omit raw chat transcripts and rely on three core components:
  1. **Artifact / Commit References**: File paths, commit SHAs, and focused diffs.
  2. **Structured State Summary**: Objective, completed items, and unresolved obstacles.
  3. **Targeted Next Steps**: Bounded scope of work and explicit acceptance criteria for the next actor.
- Avoid mechanical "last N turns" slicing in favor of context-relevant excerpts.

#### 4.2 Flash-Centric Routing with Explicit Escalation / Demotion Events (`docs/routing-guide.md`, `AGY_RULES.md`) [Adopted & Integrated]
- **Baseline**: Gemini 3.8 Flash serves as the baseline model for exploration, prototyping, implementation, and incremental edits. Reasoning effort (e.g., Low/Medium/High) is not treated as a universal default; it is selected and recorded per task or upon explicit owner specification.
- **Escalation Triggers (Promotion to Higher-Tier Model)**:
  - Repetitive failure with identical symptoms where Flash shows no clear path to resolution.
  - Reaching the agreed task limit (budget or attempts) without tangible progress.
  - Complex architectural planning or demanding independent reasoning.
- **Demotion Triggers (Return to Baseline Model)**:
  - Immediately following resolution of the blocker or architectural hurdle by the higher-tier model.
  - Reaching the bounded budget limit of the escalated model (freeze work and pause for human review if unsolved).
  - Transitioning into routine tasks (test authoring, formatting, minor cleanups).
- **Logging Rule**: Record `requested model/effort` and `observed runtime model/effort` independently; log `UNKNOWN` whenever runtime evidence is absent.

#### 4.3 Failure Taxonomy and Boundary Controls (`docs/handoff-templates.md`) [Adopted & Integrated]
- Classify and log failure causes into four categories:
  1. `Environment`: Transient network glitch, service unavailability.
  2. `Authorization`: Insufficient execution permissions, security boundary violation.
  3. `Timeout`: Unresponsive process, work limit expiration.
  4. `Quality`: Output fails acceptance rubric, test suite regressions.
- **Policy**:
  - `Authorization` failures trigger an immediate fail-closed halt. Circumvention via alternate tokens, IDs, or routes is prohibited.
  - `Environment` or `Quality` failures allow saving context once and attempting at most one authorized alternative. Runaway retry loops are forbidden.

#### 4.4 Concurrency Limits and Exit Gates (`docs/routing-guide.md`, `docs/pr-review-pipeline.md`) [Adopted & Integrated]
- **Concurrency**: Target a maximum of 2 independent tasks concurrently under manual oversight. Do not represent this as an automated parallel engine.
- **Exit Criteria**:
  - Exact match between reviewed head SHA and verified head SHA.
  - Passing CI and static validation checks.
  - Complete resolution of Blocker and Major review findings.
  - Explicit sign-off by the human Product Owner.

---

### Proposal Priority P1: Efficiency and Standardization (Integrated vs. Unimplemented Proposals)

#### 4.5 Tiered Criteria for Handoff Templates (`docs/handoff-templates.md`) [Adopted & Integrated]
- **Use Concise 4-Item Template**:
  - Routine progress updates within the same environment.
  - Low-risk edits (single-file patches, documentation formatting, bounded research summaries).
- **Use Full Evidence Manifest**:
  - Handoffs across different models, providers, or environments.
  - External system interactions, API authorizations, or sensitive boundary crossings.
  - Logging handoff failures, exceptions, or fallback events.
  - Multi-stage validation pipelines.

#### 4.6 Tiered Documentation Reviews (`docs/pr-review-pipeline.md`) [Adopted & Integrated]
- **Routine Documentation**:
  - Scope: Minor phrasing edits, typo fixes, layout tweaks.
  - Review: Lightweight single-reviewer check + deterministic markdown/link validation. Avoid redundant multi-model reviews.
- **Governance & Configuration Documentation**:
  - Scope: Access permissions, security controls, operational decisions, architectural routing.
  - Review: Full independent distinct-provider review + mandatory human acceptance.

#### 4.7 Event-Driven Quota Observation (`docs/dots-codexbar-orchestration.md`) [Unimplemented Proposal / Pending Validation]
- Eliminate periodic polling. Observe quotas manually only at designated trigger events:
  - Task intake and initial capacity check.
  - Model escalation or multi-model handoff decisions.
- If data is stale or missing, record as `unknown`; rather than an unconditional halt, transition to explicit manual selection and human verification.

#### 4.8 Deterministic Static Checks and Prompt Cache Evaluation (`tools/pipeline.py`) [Unimplemented Proposal / Pending Validation]
- **Deterministic Static Pre-checks**:
  - SHA verification, markdown link validation, whitespace trimming, and manifest schema checks must run via deterministic scripts/CLI tools, sparing LLM invocations.
- **Prompt Cache Hypothesis Testing**:
  - For tasks with large immutable context (system instructions, static references) where the provider supports prompt caching and data privacy requirements are satisfied, evaluate prompt caching.
  - Measure cache hit rates in pilot tasks rather than assuming immediate cost savings.

---

## 5. Measurement and Verification Framework (Hypothesis Evaluation)

This framework provides a pilot measurement design to evaluate operational efficiency empirically. Personal empirical baseline logs are unprovided and unverified, and no percentage reductions are guaranteed.

### 5.1 Per-Task Metric Schema
Record the following fields for each evaluated task (numbers recorded only when available):

| Metric Field | Description / Format | Objective |
|---|---|---|
| `task_id` | Unique task identifier | End-to-end traceability |
| `requested_model` | Specified model and effort label (recorded when specified) | Intended resource allocation |
| `observed_runtime` | Actual runtime model identifier (`UNKNOWN` permitted) | Verification and fraud prevention |
| `provider_pool` | Provider name and designated capacity pool | Runtime infrastructure identification |
| `subscription_quota_obs` | Subscription quota observation (window and observation timestamp; `unknown` if unobserved/stale; not mixed with API billing) | Subscription tracking without mixing into billing |
| `api_usage_billing` | API token usage and charges (recorded only when available; never commingled with subscription units or tokens) | Metered API expense tracking |
| `tokens_in` / `tokens_out` | Input and output token counts (when reported) | Resource usage quantification |
| `context_resend_count` | Number of times context/transcripts were resent | Evaluation of context redundancy |
| `escalation_reason` | Trigger for model promotion (`none` if unescalated) | Auditability of escalation rules |
| `retry_count` | Count and category (`env`, `auth`, `timeout`, `quality`) | Failure mode pattern analysis |
| `review_rounds` | Number of review iterations | Iteration overhead assessment |
| `cache_hit` | Prompt cache hit indicator / percentage | Prompt cache viability test |
| `human_effort_minutes` | Human time spent directing, reviewing, approving | Measurement of human overhead |
| `unknown_rate` | Ratio of `unknown` readings for runtime or quota | Observation fidelity tracking |
| `quality_outcome` | `accepted` / `reworked` / `rejected` | Quality gate adherence check |

### 5.2 Pilot Measurement Design
- **Sampling Scope**: 2 weeks or the first 10 representative tasks.
- **Nature**: An exploratory sample design to test data collection viability and baseline behavior, not a rigid pass/fail scorecard.
- **Verification Goals**:
  - Assess whether Flash-centric baseline sustains throughput without quality degradation.
  - Identify whether unnecessary escalations occur.
  - Measure how diff-centric handoffs affect token volume and information completeness.
  - Quantify the frequency and operational impact of `unknown` quota observations.

---

## 6. Safeguards, Quality, and Approval Gates

1. **Distinction between Fail-Closed and Manual Verification**: Authorization denials and security boundary violations trigger an immediate halt (fail-closed) with no alternate-route circumvention. Conversely, factual unknowns regarding runtime models or quota are recorded as `UNKNOWN` / `unknown` and routed to explicit manual selection and verification rather than an unconditional execution halt.
2. **Audit Integrity**: Do not omit revisions, hashes, or gate stages from evidence manifests.
3. **Zero Secret Leakage**: Public repositories, reports, and handoffs must never contain personal data, credentials, raw chat transcripts, internal network addresses, or unmasked account billing screenshots.
4. **Separation of Concerns**: User consent, local mock testing, CI verification, and production merging are treated as separate evidentiary milestones and must never be conflated.
