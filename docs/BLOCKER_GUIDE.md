# Governance Blocker Guide

When a gate prints `[GOVERNANCE BLOCKED]`, stop the denied mutation.

Read, in order:

1. `AGENTS.md`
2. `docs/GOVERNANCE_RULES.md`
3. `.governance/workspace-policy.json`
4. `.governance/task-scope.json`
5. this file

## If the reason is `NO_ACTIVE_SCOPE`, `SCOPE_UNSIGNED`, `SCOPE_SIGNATURE_STALE`, or `SCOPE_SIGNATURE_INVALID`

Do **not** activate authority by simply editing governance files.

The permitted workflow is:

```text
agent/user prepares proposed task-scope.json
→ node scripts/propose-scope.mjs
→ external operator reviews exact scope
→ operator signs exact canonical scope using external private key
→ signature is written to .governance/task-scope.sig.json
→ gate independently verifies signature
→ only then can authorized actions proceed
```

The signing private key must remain outside governed workspaces and outside agent-accessible tool context.

## If the reason is `CHANGED_OUTSIDE_SCOPE`

Restore the unrelated change, or request a new operator-signed scope **before** changing that file.

## If commit/push is blocked

The active signed scope must explicitly include `commit` and/or `push` in `allowedActions`, and the actual staged/HEAD files must all match `allowedFiles` and not match `forbiddenFiles`.
