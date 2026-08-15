---
name: workspace-completion
description: Inspect, diagnose, implement, validate, and finish a repository task cleanly. Use when fixing bugs, completing a feature slice, integrating a reasoning/guard component, reviewing a workspace, or preparing work for commit/PR without leaving duplicate paths, temporary artifacts, or unvalidated claims.
---

# Workspace completion

Use this procedure for repository implementation and debugging tasks. It is a method, not a new runtime authority.

## 0. Bind work to the current milestone
Before editing roadmap or milestone work, read `.agent/PROJECT_CONTEXT.md` and identify the currently active milestone and the exact slice requested.

For the current project state, the next major milestone is **Persistent Runtime Integration**, and the first implementation slice is **R1: live runtime ownership audit + lifecycle contract**.

Rules:
- verify the live repository before trusting the milestone baseline recorded in `.agent`;
- execute only the requested slice, not the whole milestone;
- do not pre-implement later runtime persistence, resume, retry, recovery, tool-orchestration, or repair features unless the current slice proves they are required;
- if an equivalent active runtime owner or contract already exists, extend it instead of creating another one;
- when the milestone status in `.agent` conflicts with current source, Git state, tests, or runtime evidence, follow current evidence and report the stale context.

## 1. Establish identity
Before editing, collect:
- repository root;
- current branch and HEAD;
- `git status --short`;
- relevant worktree/branch relationship when ambiguity exists;
- exact task objective and acceptance condition.

Do not create a new worktree or duplicate repository merely to inspect the task. Use the current workspace unless isolation is genuinely required by the task.

## 2. Build the smallest useful repository map
Inspect only enough structure to locate the active path:
- entry points;
- imports/exports;
- registries/catalogs;
- routers/factories/adapters;
- configuration owners;
- tests for the same capability;
- duplicate/legacy/compatibility implementations.

Track separately whether each relevant path is known, inspected, reachable, runtime-active, changed, and validated.

## 3. Classify the failure or requirement
Choose the primary class from evidence:
- structural;
- behavioral;
- runtime;
- integration;
- state;
- authority/permission;
- validation;
- performance;
- recovery.

If uncertain, inspect structure and runtime evidence before selecting an implementation pattern.

## 4. Prove the owner
Trace from the observed behavior or requested capability to the earliest authoritative component.

Before editing, answer:
- What component owns the operation or canonical state?
- Is there another implementation of the same capability?
- Is this file registered/reachable or merely present?
- Is a legacy/test/generated path being mistaken for runtime code?
- Would this edit create a second owner or parallel contract?

For authority-sensitive work, prefer one explicit owner with bounded delegates/observers/projections. Do not infer duplicate authority from duplicate storage alone.

## 5. Inspect contracts before changing code
Read the current contracts, schemas, guard metadata, tests, and orchestration boundary for the affected component.

For this repository preserve these authority boundaries:
- reasoning interprets/selects/explains/proposes;
- retrieval supplies reference context;
- workspace inspection supplies current facts;
- deterministic guards produce guard truth;
- validation proves the result;
- governance/LBE authorizes mutation;
- controller/orchestrator coordinates and must not absorb those authorities;
- persistent runtime owns only session/task lifecycle, orchestration state, checkpoint/recovery state, and lifecycle evidence.

Never promote indexed reference evidence into current workspace truth.

## 6. Choose the smallest correct change
- Reuse existing types and services before introducing new ones.
- Do not create a parallel planner, gatekeeper, validation layer, proposal engine, verdict path, session owner, or runtime state owner when an existing owner can be extended.
- Keep changes task-scoped.
- Do not mix cleanup/refactoring with a feature fix unless the cleanup is required for correctness.
- Do not implement deferred roadmap capabilities as side effects of the current task.

If repository evidence contradicts the requested plan, stop implementation and report the contradiction with exact paths/evidence.

## 7. Test the contract first when practical
For behavior or regression work:
1. add/update the smallest focused regression test that expresses the required contract;
2. run it and confirm the expected failure when useful;
3. implement the smallest fix;
4. rerun focused tests.

Do not create tests that merely encode the current implementation when the intended contract is different.

## 8. Validate by evidence level
Use the minimum evidence sufficient for the claim, escalating as required:

```text
source proof
-> static/build proof
-> unit/contract proof
-> integration proof
-> runtime proof
-> user-visible proof
```

Examples:
- contract helper changed -> focused unit/contract tests;
- controller wiring changed -> controller + provider/integration tests;
- `/reasoning/run` claim -> live route/runtime proof when available;
- persistent runtime claim -> process/session lifecycle proof including stop/resume when applicable;
- packaging/release claim -> build + fresh install + installed-artifact smoke;
- UI/runtime claim -> user-visible action plus backend consequence.

Never translate "command exited 0" into "feature works" without matching validation.

## 9. Run a bounded second scan
After the fix, inspect the affected neighborhood for:
- duplicate routes or functions;
- alternate adapters/providers;
- stale compatibility paths;
- multiple state/config owners;
- multiple session/task/runtime owners;
- test-only implementations mistaken for runtime paths;
- hardcoded fallback behavior that bypasses the new owner.

Do not rescan the entire repository without a task-driven reason.

## 10. Finish cleanly
Before declaring completion:
- remove transient patch/test-output files created during the task;
- ensure generated/runtime/local-secret files were not staged;
- run the required full repository test suite when the change affects shared behavior;
- run `git diff --check`;
- run `git status --short`;
- inspect the final diff/stat and verify only intended files changed.

Completion requires:

```text
intended change exists
AND active path uses it when applicable
AND required validation passed
AND observed behavior matches the objective
AND no in-scope blocker remains
AND the working tree contains no accidental artifacts
```

## 11. Report briefly
Return only:
- what was wrong / what requirement was implemented;
- exact files changed;
- validation results;
- remaining blocker or risk, if any.

Do not produce speculative follow-up work when the current slice is complete. Do not claim success if required evidence is missing.