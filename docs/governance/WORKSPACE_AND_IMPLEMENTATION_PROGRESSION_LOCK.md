# Workspace and Implementation Progression Lock

Status: **AUTHORITATIVE GOVERNANCE GATE — ACTIVE ON `main`**

## Purpose

Prevent branch/worktree drift and prevent agents from advancing implementation or inventing parallel architecture without proof.

## Canonical workspace authority

Implementation and delivery authority is limited to:

```text
repository: Letterblack0306/LBE_Presistent_Agent_wall
remote: origin
branch: main
worktree: primary Git worktree
push target: origin/main
```

Any other branch, detached HEAD, secondary worktree, alternate remote, or non-main push target is blocked for governed implementation/delivery.

Side branches and secondary worktrees may be inspected as read-only reference material. They are not implementation authority.

## Mandatory preflight before any write-capable step

The agent must establish all of the following from live Git/workspace evidence:

1. canonical repository identity;
2. current worktree is the primary worktree;
3. current branch is exactly `main`;
4. HEAD is attached to `refs/heads/main`;
5. remote is exactly `origin` and resolves to the canonical repository;
6. no merge/rebase/cherry-pick/revert is in progress;
7. `.lbe/governance/implementation-gates.json` permits the current slice;
8. deep workspace inventory has classified tracked, untracked, ignored, hidden, nested, generated, stale, copied, backup, temp, and agent-created files or explicitly excluded them by rule.

If any item is not proven, classify the step as `BLOCKED_WORKSPACE_AUTHORITY` and stop write-capable work.

## Deep workspace inventory blocker

Agents must not only inspect noticeable root files or ordinary Git status output.

Before any new authority investigation, implementation slice, patch, validation claim, or forward progression, the agent must prove what exists across the full workspace depth.

This gate covers:

- tracked files;
- untracked files;
- ignored-but-present files;
- hidden root entries;
- nested hidden files and folders;
- nested package roots;
- generated/runtime folders;
- stale validation output;
- report, receipt, proof, audit, checkpoint, backup, copy, temp, and agent-created files;
- copied repositories or nested workspace roots;
- any file or folder that could be mistaken by a future agent for current authority.

Required classification labels:

```text
CANONICAL
GENERATED_ALLOWED
RUNTIME_ALLOWED
HISTORICAL_REFERENCE
STALE_AGENT_OUTPUT
UNKNOWN_OWNER
DELETE_CANDIDATE
BLOCKED_UNTIL_CLASSIFIED
```

Hard blocker:

```text
UNCLASSIFIED_DEEP_WORKSPACE_CONTENT
```

Trigger:

```text
Any disk-present file, folder, hidden path, ignored artifact, nested package root, generated output, backup, report, receipt, proof, checkpoint, temp file, copied workspace, or agent-created file exists without classification or explicit exclusion by rule.
```

Rules:

```text
No deep inventory = no next investigation.
No classification = no patch.
Ignored does not mean nonexistent.
Untracked does not mean irrelevant.
Hidden does not mean safe.
Visible root inspection is not workspace proof.
Git status alone is not workspace proof.
```

If this blocker is triggered, the agent must stop before Authorization/Governance Ownership, owner-boundary traces, or implementation work.

## Mandatory implementation checkpoints

Every implementation slice must follow this sequence:

```text
G0 authoritative plan loaded
G1 canonical workspace/main/primary-worktree proven
G1A deep workspace inventory complete and non-obvious files classified
G2 exact base SHA recorded
G3 existing owner(s) inspected
G4 reuse/adaptation options evaluated
G5 bounded slice contract recorded
G6 only the approved slice implemented
G7 focused validation completed
G8 required integration/runtime/user-flow evidence completed
G9 checkpoint record completed
G10 current slice explicitly PASS
G11 only then unlock the next slice
G12 delivery allowed only from canonical main
```

`FAIL`, `UNVERIFIED`, `DOCUMENT_CONFLICT`, `MISSING_EVIDENCE`, `UNKNOWN_OWNER`, `BLOCKED_UNTIL_CLASSIFIED`, or `UNCLASSIFIED_DEEP_WORKSPACE_CONTENT` blocks forward progression.

A unit test cannot satisfy a LIVE_RUNTIME or USER_FLOW requirement. Evidence must match the level of the claim.

## Architecture creation blocker

Agents must not create a new owner for an already-owned responsibility merely because a new implementation is convenient.

Protected ownership categories include at least:

- workspace/project identity;
- session/task persistence;
- provider/model capability truth;
- authorization;
- governed tool dispatch;
- operation identity/idempotency;
- runtime-event persistence;
- checkpoint/recovery;
- evidence provenance;
- validation truth;
- completion truth;
- control protocol semantics.

Before any new architecture/owner is created, all of the following are required:

1. exact existing owner identified and inspected;
2. requirement that the existing owner cannot satisfy is documented;
3. reuse/adaptation of existing project code and planned third-party reusable layers is evaluated;
4. incompatibility is supported by evidence rather than preference;
5. architecture change is explicitly authorized by the user;
6. canonical architecture/plan documents are updated first;
7. the implementation gate is changed to allow that architecture change.

Otherwise: `BLOCKED_PARALLEL_ARCHITECTURE`.

## Reuse-before-rebuild rule

Where the active plan identifies an existing implementation or reusable dependency, evaluation of that path is a mandatory gate before parallel implementation.

For professional provider/continuation work this includes the active Cline reuse direction when/where it is made canonical: evaluate the lowest useful Cline layer first and preserve LBE authority. Do not build redundant provider transport or continuation architecture merely because a prototype is easier.

## Delivery rule

The repository ships a versioned `pre-push` hook under `.githooks/`. After pulling this governance change, enable it once with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/enable-workspace-lock.ps1
```

The hook fails closed unless the push originates from the primary worktree on `main` and targets `origin/main`.

This local hook does not protect against an identity that can directly mutate GitHub refs through the API. Remote repository rules/permissions must separately prevent agent identities from creating/updating non-main branches if that threat model applies.

## Supersession note

Historical plan/acceptance records may mention feature branches or secondary worktrees. Those records remain historical evidence. From this governance gate forward, they do not authorize new implementation/delivery outside canonical `main`.
