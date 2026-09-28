# Letterblack Governed Workspace

Before any mutation, read:

1. `docs/GOVERNANCE_RULES.md`
2. `.governance/workspace-policy.json`
3. `.governance/task-scope.json`
4. `docs/BLOCKER_GUIDE.md`

## Mandatory behavior

- Do not treat documentation as authorization.
- Do not mutate source without a valid externally signed active scope.
- Do not edit scope/signature files merely to make a blocked action pass.
- Scope proposals are not authorization.
- If the gate blocks, follow `docs/BLOCKER_GUIDE.md`.
- Before direct filesystem/shell/Git mutations, use the governed controller or `node scripts/action-preflight.mjs <action> [target]` where integrated.
- Do not claim enforcement for any mutation route that bypasses governance.

## Blocked state

If no signed scope exists, report the blocker and the exact scope/action required. The external operator must authorize it.
