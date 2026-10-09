# Letterblack Governed Workspace

Before any mutation, read:

1. `docs/GOVERNANCE_RULES.md`
2. `.governance/workspace-policy.json`
3. `.governance/task-scope.json`
4. `docs/BLOCKER_GUIDE.md`

## Mandatory behavior

- Do not treat documentation as authorization.
- Mutations require an active locked task scope whose file/action boundaries cover the operation.
- No external signature, operator key, detached signature, or signing ceremony is required.
- If the gate blocks, follow `docs/BLOCKER_GUIDE.md`.
- Before direct filesystem/shell/Git mutations, use the governed controller or `node scripts/action-preflight.mjs <action> [target]` where integrated.
- Do not claim enforcement for any mutation route that bypasses governance.

## Blocked state

If no active locked scope exists, report the exact missing scope/action. Once the authorized scope and required validation pass, normal commit/push may proceed when those actions are allowed.

## Standing development authorization

Follow the standing authorization section of docs/GOVERNANCE_RULES.md: the active scope permits normal enhancements, bug fixes and removal of unwanted code; a blocked acceptance slice or one unavailable provider does not halt unrelated authorized work. Keep genuine workspace/effect boundaries and test real effects.
