# Cookbook 06: Repository Maintenance

[English](06-repository-maintenance.md) | [日本語](06-repository-maintenance.ja.md)

The public repository contains only reusable operating guidance and evidence state, not private work context. When current user-authorized work leads to a documentation update, describe it generally and keep implementation, local verification, and runtime status separate.

## Before editing

1. Inspect repository status and preserve existing user changes.
2. Confirm the latest default branch and relevant source evidence.
3. Create an isolated branch/worktree; do not overwrite unrelated changes.
4. Identify English/Japanese pairs and check their links.

## While editing

- For GitHub code changes, update affected README, usage, and design documentation, including existing English/Japanese counterparts. Keep the two languages aligned.

- Use the task-based selection rules in the [routing guide](../routing-guide.md).
- Label owner-reported model names as such; never invent CLI IDs or runtime availability.
- Keep Dottie (PM), AI Governance Control (thin handoff/artifact/evidence), and AIteamBridge (local capacity/router/transport project) responsibilities distinct.
- Use `verified/merged`, `local/offline`, `runtime pending`, and `proposal` consistently.
- Do not publish private conversations, credentials, quota screenshots, account balances, personal/family details, or connection identifiers.
- Ensure proposed architecture is not described as deployed or automatically operating.

## Before integration

- Check links, bilingual references, whitespace, and old claims.
- Review the changed-file list and diff for secrets or private context.
- Report checks and blockers precisely. Approval of a direction, an accepted request, execution, local test success, and production reflection are distinct states.
