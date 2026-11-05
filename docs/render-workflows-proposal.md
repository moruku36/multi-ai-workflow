# Proposed Render Workflows role

[English](render-workflows-proposal.md) | [日本語](render-workflows-proposal.ja.md)

Status: **proposal only**. Official public references checked on 2026-11-05 (UTC). This note does not establish an installed SDK, deployed workflow, authorized API route, accepted review quality, or live autonomous operation. Existing dated architecture records remain unchanged.

## Where it fits

Render Workflows is a candidate execution layer for bounded, on-demand multi-AI jobs: collect public sources, call approved model APIs, combine results, and return evidence for human acceptance. It does not replace the resident coordinator, the mailbox, or the repository review contract.

A proposed sequence is: authorized request → validate scope and budget → collect public inputs → run a bounded set of provider tasks → aggregate findings → record evidence → coordinator review. A successful run is execution evidence, not permission to publish, merge, send messages, or deploy. Different task instances do not establish independent review; the actual reviewer provider and exact reviewed revision still matter.

Suitable examples are a public-source comparison, a draft assembled from already-cleared material, or a limited review of public code. Start with a harmless fixture and no live model calls. Private conversations, personal information and secrets are excluded from this proposal's inputs and outputs.

## Product boundaries

[Render's overview](https://render.com/docs/workflows) describes Python/TypeScript tasks and flows, managed queuing, on-demand instances, retries and run inspection. Tasks can chain tasks; flows persist ordered step results for replay. Do not assume these APIs are interchangeable: the current overview lists flow-to-task/flow chaining as unsupported. Runs do not expose incoming ports. When all runs finish, execution scales to zero; this does not mean every related charge disappears.

Workflows is distinct from a continuously running background worker and from a cron job. Native scheduling is currently listed as unsupported; scheduled triggering would need a separate scheduler and separate approval. This proposal uses on-demand triggers only.

## Render and Vercel

| Choice | Proposed reason to consider it | What still needs checking |
| --- | --- | --- |
| Render Workflows | Separate task-oriented execution, configurable task compute and an execution boundary outside the user-facing application | Current SDK, region, quotas, state retention, task/flow restrictions and whole-job cost |
| Vercel Workflows | Durable multi-step work closely integrated with an application already on Vercel | Current workflow/step limits, deployment coupling, retention and total platform cost |
| Keep the existing route | A small, already-working job needs no new platform | Whether it meets time, retry, audit and cost requirements |

[Vercel also supports durable workflows](https://vercel.com/docs/workflows), including retries, persisted state and waiting/resuming. It is not merely a frontend host. A possible split is Vercel for the application and Render for selected jobs, but the extra authentication, monitoring and failure boundaries must justify it. No migration or cheapest-platform conclusion is implied.

## Budget before any live trial

Use the current [Render limits and pricing](https://render.com/docs/workflows-limits), not a remembered free allowance. Billable components include run compute, retained run/step state and applicable outbound bandwidth; external model APIs and any added storage or scheduler are separate. Fixed compute plans charge by duration; the flex plan depends on CPU/RAM usage and has a minimum charge. Count parent and child runs, retries, and failed attempts. Scaling to zero does not erase retained-state charges or other services' bills.

Before approval, estimate the entire bounded job in the billing currency and specify: maximum runs and fan-out, concurrency, timeout, retry count, input/output sizes, per-provider token limits, and total cost ceiling. Do not assume provider limits or an alert enforce that ceiling. Require a tested application-side admission/stop policy; if remaining budget or price is unknown, do not start another run. An uncertain external response must not be blindly repeated because a retry can duplicate both side effects and charges.

## Authentication, secrets and safe operation

- A future caller must authenticate and authorize the requester before triggering work. Validate allowed task names and input schemas; deduplicate requests and reject replay. The caller, not arbitrary model output, decides the permitted action.
- Render access and model-provider access are separate. Use approved server-side secret storage and least privilege. Never place credentials in browser code, repository files, run arguments, returned values, or logs. Creating credentials or granting persistent access needs its own approval.
- Treat arguments, outputs, errors and tracing as potentially retained data. Redact before submission; reference authorized artifacts rather than embedding sensitive documents. Confirm retention and access rules before expanding beyond public inputs.
- Use bounded retries and idempotency for side effects. Cancellation/timeout is not proof that an external request did not execute. Verify outcome before repeating it.
- A task result never grants new permissions. Keep publication, GitHub merge, deployment and any consequential action behind their existing approvals and gates.

## Adoption and evidence checklist

1. Pin a compatible SDK and define one public/synthetic fixture; record expected output and failure cases.
2. Validate locally without cloud deployment, new credentials or paid provider calls. Record exact revision and commands; mock success is only local evidence.
3. Separately approve the workspace, region, data destinations, credentials/access, trial budget and stop conditions before provisioning or live calls.
4. Run one bounded trial only after approval. Record start/terminal status, redacted output, retry/failure behavior and measured total cost. A created run ID is not completed execution.
5. Obtain the required exact-head, separate-provider review and deterministic checks before accepting repository changes or expanding operation. Follow the [review contract](pr-review-pipeline.md).
6. Keep documented, locally tested, deployed, executed and accepted states separate. Stop expansion if evidence, permissions or budget are missing.

This documentation change creates no Render service, scheduler, deployment, API credential or paid workload. It does not modify runtime or repository security settings.
