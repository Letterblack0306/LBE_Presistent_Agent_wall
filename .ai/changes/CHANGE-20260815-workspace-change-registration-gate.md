# CHANGE-20260815 — Workspace change registration gate

Status: active — implementation present, runtime validation pending

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

For this repository:

- every governed implementation mutation requires an active change intent;
- canonical `main` requires intent but does not require redundant branch/worktree fields;
- a non-canonical branch must register the exact branch name;
- a linked Git worktree must additionally register its exact `worktreePath`;
- supplied branch/worktree registration must match current Git state;
- intent scope/exclusions are checked before the write handler.

## Active owner

`lbe_guard_inspector/runtime/tool_orchestration.py` remains the mutation lifecycle owner. The change-registration checker is a precondition used by this owner; it is not a second write or authorization engine.

## Implemented scope

- `.ai/change-gate.json` — repository opt-in and gate policy;
- `.ai/intent.example.json` — active intent shape;
- `.ai/intent.json` ignored as machine-local active registration;
- this durable change record;
- `lbe_guard_inspector/runtime/change_registration.py` — Git/intent/scope checker;
- `lbe_guard_inspector/runtime/tool_orchestration.py` — pre-write invocation before R6C/handler execution;
- `tests/test_change_registration_gate.py` — focused branch/worktree/orchestrator coverage.

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
- non-canonical branch requires exact branch registration;
- linked worktree additionally requires exact worktree registration;
- mismatched branch/worktree blocks;
- matching registration permits the request to continue to normal R6C authorization;
- read-only tools are unaffected;
- focused tests pass;
- broader affected runtime tests pass;
- `git diff --check` equivalent review passes on final branch.

## Current validation state

- GitHub PR #56 created as draft at head `4cecdbebc926400ea37808d813ebbeb35fd19d69` before this documentation reconciliation commit.
- GitHub `validate` and `v2-release-candidate` workflows failed at startup: all matrix jobs reported failure with zero executable steps/logs, so they provide no test verdict.
- Independent container validation could not clone GitHub because the execution environment had no DNS/network access.
- Therefore this change is **IMPLEMENTED but not yet RUNTIME-VALIDATED**. Do not merge or claim completion until the focused and affected regression suites are executed successfully on the current final head.

## Limitation

Repository code cannot prevent an unrelated external editor/process from writing directly to disk outside the LBE governed tool path. This gate is a pre-mutation blocker for LBE-governed agent tools. Commit/push/CI documentation gates are a separate enforcement layer and may be added independently if required.
