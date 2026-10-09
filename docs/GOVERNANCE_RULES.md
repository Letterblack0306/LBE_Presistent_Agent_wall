# Letterblack Standard Workspace Governance — v1

Policy ID: `LB-WORKSPACE-GOVERNANCE-V1`

## Core invariant

> The agent must not be able to turn a false claim into authorization by writing more governance text.

Authorization comes from pre-existing machine-readable scope and policy. Facts come from current machine-observable state. Proof comes from observed effects. Documentation describes those facts; it does not create them.

## Non-negotiable rules

- Documentation is not authorization.
- Policy presence is not policy use.
- Implemented is not proven.
- PASS is not working.
- Exit 0 is not the requested effect.
- Emitted is not executed.
- Returned is not consumed.
- Persisted is not rehydrated.
- UI state is not runtime state.
- Agent claim is not machine evidence.
- Index entry is not repository fact.
- Clean worktree is not valid commit proof.
- Unknown evidence remains unknown.
- Governance/evidence failures fail closed.

## Standing authorization: governance enables delivery (2026-10-09)

Governance protects workspace identity, prevents drift, and records evidence. It is NOT an independent feature veto, a ban on enhancements/removals, or a substitute for the user's product decisions.

The user's continuous-maintenance scope already authorizes ordinary bug fixes, features, refactoring, removal of unwanted/obsolete code, tests, and follow-up changes. Do not ask for repetitive authorization for any of these when covered by the active scope.

Run: inspect current workspace -> identify implementation owner -> register bounded intent -> change and test -> verify actual effects -> reconcile documentation -> commit and push when authorized. Do not replace action with discussion.

A blocked or unverified acceptance slice describes evidence, not permission to change code. Likewise, an optional provider outage (including LM Studio), optional dependency failure, old test result, or unrelated dirty/untracked artifact is a localized condition, never a blanket stop. Isolate it, preserve unrelated changes, continue independent authorized work, and state exactly which acceptance remains open.

Scoped deletion is a legitimate maintenance action. Defective or obsolete features must not be retained merely because deletion is perceived as forbidden. Structural changes require accurate index maintenance, not a new user approval when within scope.

Real effect-level authorization stays in force for secrets, forbidden paths, destructive actions outside the requested scope, other users' resources, and separate release/publication/force-push authority. Classify a denial by its actual action and cause. Never bypass those protections, fabricate permission, or claim a test PASS proves the product works.

If one effect truly requires authorization beyond existing scope, stop ONLY that effect; continue all independent authorized steps. Ask for the specific missing authorization only if indispensable.

## Governance layers

1. Workspace policy: global invariants for this workspace.
2. Task scope: the files and actions allowed for the current task.
3. Action decision: the specific proposed mutation.

## Required execution sequence

```text
WORKSPACE IDENTIFIED
→ POLICY LOADED
→ ACTIVE SCOPE ESTABLISHED
→ REQUIRED CONTEXT RECEIPTED
→ INTENT REGISTERED
→ BEFORE SNAPSHOT
→ ACTION PROPOSED
→ POLICY DECISION
→ AUTHORIZED EXECUTION
→ ACTUAL EFFECT
→ OBSERVATION
→ VALIDATION
→ AFTER SNAPSHOT
→ PROOF
→ RECEIPT
→ TERMINAL CLASSIFICATION
```

## Scope rules

- Scope must exist before implementation begins.
- Changed files must be inside `allowedFiles`.
- `forbiddenFiles` always deny.
- When `scopeLocked=true`, implementation and scope expansion must not occur in the same change.
- A changed file outside scope is `CHANGED_OUTSIDE_SCOPE`; it is not permission to extend scope automatically.
- Governance authority files must not authorize their own mutation.

## Generated indexes

Human-readable indexes such as `PROJECT_INDEX.md` or `AGENT_INDEX.md` are observations only. They must never grant authority.

Claims such as these must be derived where mechanically possible:

```text
FULLY_READ: YES
CALLERS: NONE
CONSUMERS: NONE
TARGET_STATUS: VALID
PROVEN_DEAD_CODE
WORKING
SAFE
AUTHORIZED
APPROVED
```

## Source lifecycle

Recommended states:

```text
active
loaded-by
adapter
compatibility-wrapper
generated
experimental
deferred
deprecated
removed
ignored
```

A lifecycle declaration does not override current repository facts.

## Git gates

Governance should evaluate separately:

- worktree state during active work;
- staged state before commit;
- `HEAD` after commit / before push;
- remote alignment when proving synchronization.

A clean worktree must not cause a committed tree to be considered valid automatically.

## Completion

`COMPLETE` or `CLEAN` is allowed only when the requested effect is observed, actual changes remain inside approved scope, forbidden boundaries remain intact, required validation/proof exists, and no material falsifier remains.

## Enforcement claim boundary

This kit can enforce the Git/workspace gates it is actually wired into. It must not claim exclusive enforcement while direct write, shell, MCP filesystem, native host, or other bypass mutation routes remain available outside the controller.

## Governance changes

After initial installation, governance authority should be changed only in a separate governance-only change. Use a task scope with `mode: "GOVERNANCE"`, limit `allowedFiles` to the exact governance resources being changed, and do not mix implementation files into that change. This Git-level kit cannot authenticate who authored the governance scope; stronger installations must bind scope activation to an external controller/user approval or LBE decision token.
