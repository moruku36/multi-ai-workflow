# Cloud Access Guide: Read-Only Billing and Metadata (Windows, CLI First)

Japanese: [05-cloud-access-readonly.ja.md](05-cloud-access-readonly.ja.md) | English: [05-cloud-access-readonly.md](05-cloud-access-readonly.md)

This guide is documentation only. It authorizes no cloud operation, and nothing in it was executed to write it. It does not change routing policy. Human approval of a PR or merge does not authorize cloud operations.

## Purpose and Principles

- The CLI authenticates the cloud principal. The AI coordinates and runs one bounded, approved operation. A model subscription is not cloud IAM.
- Each AI may use the same existing local authenticated CLI session, if the owner authorizes it. Never copy credentials between models, hosts, files, or repositories.
- Windows is the primary host. Use the CLI first. Fall back to the authenticated existing Chrome GUI only when CLI billing is unavailable or chargeable.
- Before claiming access, inspect the installed CLI version, its supported commands, and the account scope.
- Do not install anything or log in anew without action-time approval.

## Approved Scope

Use an exact private allowlist, kept outside this repository: owner-confirmed AWS account, profile, and regions; Azure subscription; GCP billing account and project. Exclude company or unknown scopes.

- AWS: regional observations do not cover all services or regions.
- Azure: always pass an explicit `--subscription`. Never run `az account set`.
- GCP: always scope to an explicit project.

## Read-Only Commands (Generic Examples)

These are examples only. Placeholders must be replaced from the private allowlist.
Compare the returned account, subscription, and billing/project association with that allowlist before any resource or billing read. Keep metadata outputs private; redact identifiers, ARNs, and email addresses before a handoff or publication.

```
aws --version
aws sts get-caller-identity --profile "<PROFILE>" --region "<REGION>"
az account show --subscription "<SUBSCRIPTION_ID>"
gcloud --version
gcloud billing accounts describe "<BILLING_ACCOUNT_ID>" --project "<PROJECT_ID>"
gcloud billing projects describe "<PROJECT_ID>" --project "<PROJECT_ID>"
```

Do not run commands that print credentials, tokens, or debug output. Do not run commands that may auto-install extensions or auto-enable APIs.

## Billing Evidence

- AWS: use the free Bills page, `https://console.aws.amazon.com/billing/home#/bills`. The Cost Explorer API costs $0.01 per primary-view request, so avoid it unless a spending limit is separately approved. Do not enable Cost Explorer, add-ons, or anomaly monitors through dashboard navigation.
- Azure: Cost Management Query is read-only and has no additional cost. ActualCost is not the net payable, so check credits and taxes separately. Blank rows or no ARM resources do not prove no usage. Data lag is typically 8-24h for EA/MCA and up to 72h for PAYG.
- GCP: `gcloud billing` returns metadata, not daily usage charges. Use the existing authenticated Reports page. Do not scan BigQuery or enable export. Data usually arrives within a day, sometimes later than 24h.

Record: actual vs forecast; gross usage, free tier, credits, and net; currency; usage or invoice period and timezone; last update and lag; daily and per-service detail; exact scope; and pagination. Zero net does not prove zero usage or zero future cost. This document asserts no current balance, and owner-reported actual fees are not published.

## Evidence Categories

- **owner-reported**: stated by the owner, not independently checked.
- **CLI-verified**: returned by a CLI call in the approved scope.
- **GUI-observed**: seen in the authenticated browser session.
- **incomplete**: partial, stale, or blocked. Say what is missing.

## Troubleshooting

| Symptom | Action |
|---|---|
| CLI permission or auth failure | Report the exact smallest owner step. Do not log in or create tokens. |
| `-p`/manual run without an approval host | `permission_denials` may be recorded with no GUI prompt. Exact named per-invocation read tools through normal approval review differ from stored permission changes. Never use bypassPermissions. |
| Multiple browser devices | Bind the explicit user-selected Windows device. |
| Session tabs_context omits existing console tabs | Use supported reuse, or report the limitation. Do not guess tab IDs, session stores, or private endpoints. |
| Site permission | A separate layer. Report a prompt only if observed. A new grant needs action-time approval. Do not hunt for invisible prompts. |
| Sign-in redirect | Does not prove a global sign-out. |
| Renderer progress or gstatic error | Not a fee of zero. Use bounded normal reads, or an approved public fallback URL actually observed. Do not change network, security, or browser settings, and do not assume screenshot permission. |

## Read-Only Boundary

Do not create, start, stop, or delete resources. Do not change budgets, policies, subscriptions, IAM, or security settings. Do not provision a cloud shell, run paid queries, or set automatic schedules. New persistent authentication, OAuth, API keys, or permissions need separate approval. This guide does not authorize deletion.

## Private Handoff Template

Keep filled copies and logs out of the public repo.

```
Executor / principal: <NAME> / verification status: <verified|unverified> (no secrets)
Approved scope: <PROVIDER, ACCOUNT_ALIAS, REGION/PROJECT>
Operation / tools: <OPERATION> / <TOOLS>
Evidence category: <owner-reported|CLI-verified|GUI-observed|incomplete>
Period / currency / last update / lag: <...>
Gross / credits / net: <...>
Checked scopes: <...>   Inaccessible scopes: <...>
Next owner action: <...>
```

## Sources

- [AWS Cost Explorer pricing](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/pricing/)
- [AWS: viewing your bill](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/getting-viewing-bill.html)
- [aws sts get-caller-identity](https://docs.aws.amazon.com/cli/latest/reference/sts/get-caller-identity.html)
- [az account](https://learn.microsoft.com/en-us/cli/azure/account?view=azure-cli-latest)
- [Understand Cost Management data](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/understand-cost-mgt-data)
- [GCP billing reports](https://docs.cloud.google.com/billing/docs/how-to/reports)
- [gcloud billing accounts describe](https://docs.cloud.google.com/sdk/gcloud/reference/billing/accounts/describe)
- [gcloud billing projects describe](https://docs.cloud.google.com/sdk/gcloud/reference/billing/projects/describe)
- [Claude Code headless](https://code.claude.com/docs/en/headless)
- [Claude Code in Chrome](https://code.claude.com/docs/en/chrome)
