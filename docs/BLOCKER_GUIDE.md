# Governance Blocker Guide

When a gate prints `[GOVERNANCE BLOCKED]`, stop the denied mutation.

Read, in order:

1. `AGENTS.md`
2. `docs/GOVERNANCE_RULES.md`
3. `.governance/workspace-policy.json`
4. `.governance/task-scope.json`
5. this file

## Scope activation

Authorization uses the active locked `.governance/task-scope.json`. There is no external signature, operator key, detached signature, or signing step.

The scope must declare the intended files and actions before execution. File/action allowlists and forbidden boundaries remain fail-closed.

## If the reason is `NO_ACTIVE_SCOPE` or `SCOPE_NOT_LOCKED`

Create or select the task scope for the user-authorized work, set `active: true` and `scopeLocked: true`, then run the applicable preflight/check.

## If the reason is `CHANGED_OUTSIDE_SCOPE`

Restore the unrelated change or update the task scope to the user-authorized boundary before changing that file.

## If commit/push is blocked

The active scope must include `commit` and/or `push` in `allowedActions`. Staged/HEAD files must match `allowedFiles`, avoid `forbiddenFiles`, and required validation must pass before publication.
