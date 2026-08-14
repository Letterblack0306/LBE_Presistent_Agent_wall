# CHANGE-20260815 — Workspace change registration gate

Status: active

## Registration

- Repository: `Letterblack0306/LBE_Presistent_Agent_wall`
- Branch: `agent/workspace-registration-blocker`
- Base: `feat/c5-governed-coding-execution`
- Intent: add a fail-closed change-registration prerequisite so governed workspace mutations cannot proceed after branch/worktree/task context is forgotten.
- Change type: governance/runtime safety
- Risk: medium
- Touches runtime: yes
- Touches architecture: yes — extends the existing governed tool precondition path only
- Touches release: no

## Objective

Reuse the GPT-Knowledge governed-repository pattern: meaningful implementation work must have a durable current intent declaration, while module-health/staleness remains separate and non-blocking.

For this repository, every governed implementation mutation must have an active change intent. If the current Git branch/worktree is not the canonical main workspace, the active intent must also match the exact branch and worktree identity.

## Active owner

`lbe_guard_inspector/runtime/tool_orchestration.py` remains the mutation lifecycle owner. The change-registration checker is a precondition used by this owner; it is not a second write or authorization engine.

## Intended scope

- `.ai/change-gate.json`
- `.ai/intent.example.json`
- `.ai/changes/CHANGE-20260815-workspace-change-registration-gate.md`
- `lbe_guard_inspector/runtime/change_registration.py`
- `lbe_guard_inspector/runtime/tool_orchestration.py`
- focused tests for registration and pre-write blocking
- concise design/usage documentation if required

## Must remain unchanged

- read-only inspection remains available without an implementation intent;
- R6C remains the permission/capability authority;
- registered write handlers remain the only LBE mutation implementations;
- provider/model cannot fabricate or widen registration;
- module maintenance warnings must not become this hard gate.

## Validation required

- missing intent blocks a governed write when the repository gate is enabled;
- malformed/inactive intent blocks;
- implementation intent is required even on canonical `main`;
- alternate branch/worktree requires exact branch + worktree registration;
- mismatched branch/worktree blocks;
- matching registration permits the request to continue to normal R6C authorization;
- read-only tools are unaffected;
- focused tests pass;
- broader affected runtime tests pass;
- `git diff --check` equivalent review passes on final branch.

## Limitation

Repository code cannot prevent an unrelated external editor/process from writing directly to disk outside the LBE governed tool path. This gate is a pre-mutation blocker for LBE-governed agent tools. Commit/push/CI documentation gates are a separate enforcement layer and may be added independently if required.
