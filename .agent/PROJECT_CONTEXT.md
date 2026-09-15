# Project Context for Local Coding Agents

## Purpose

This repository implements a focused LBE Guard Inspector and reasoning layer for software workspaces. The local coding agent is responsible for completing repository tasks cleanly and evidentially; it is not an additional authority layer inside the product.

Use this document as project context. Operational behavior is defined in `.clinerules/00-workspace-discipline.md`; the reusable implementation/debugging procedure is `.cline/skills/workspace-completion/SKILL.md`.

## Product objective

The system should accept a normal user problem such as:

- why is this feature failing?
- check whether this workspace follows the relevant rules;
- explain the deterministic result;
- propose a workspace-specific protection when verified evidence justifies it.

The integrated reasoning flow is:

```text
user problem
-> resolve workspace identity
-> retrieve bounded indexed reference knowledge
-> inspect current workspace evidence when required
-> LLM interprets/selects/requests evidence
-> deterministic guard execution
-> validation
-> LBE/governance state
-> bounded LLM explanation
-> optional governed workspace-rule proposal
-> normal user-facing response
```

No separate command-machine interaction should be required for ordinary user requests.

## Current verified milestone baseline

At the time this project context was updated:

```text
repository: Letterblack0306/LBE_Presistent_Agent_wall
canonical local workspace: C:\Agents-Memory-Tool-v6-integration
main merge commit: baea87694337e56c4b12618d75528f2b7abec266
merged feature head: cd0b7031ec1026adb9ea4f681630de4f3d806008
latest validated full suite for that feature head: 468 passed
```

PR #27 completed the normal LLM/controller proposal integration. The reasoning layer can now carry an optional model proposal candidate through the existing provider/controller path, govern it through the existing `ProposalPlanner` / `RuleGatekeeper`, and serialize the optional read-only proposal through the normal `/reasoning/run` response.

Always verify the live repository before relying on these revision or test values.

## Authority boundaries

Keep these owners distinct:

```text
LLM reasoning
  interprets problems
  selects likely guards
  requests evidence
  explains deterministic findings
  may propose a workspace-rule candidate

Retrieval/index
  supplies ranked reference knowledge
  never proves current workspace truth

Workspace inspection
  supplies current facts, paths, hashes, configuration, and bounded runtime evidence

Deterministic guards
  own guard-condition truth

Validation
  owns proof that the claimed condition/result is established

LBE / governance
  owns workspace identity, scope, policy, capability, approval requirements, mutation authority, audit, and completion proof

Controller/orchestrator
  coordinates the above
  must not absorb their authority

Persistent runtime
  owns long-running session/task lifecycle, orchestration state, checkpoint/recovery state, and lifecycle evidence
  must call the reasoning layer rather than reimplement it
```

Never create a second verdict path, approval path, mutation authority, proposal engine, reasoning engine, or canonical state owner when an existing owner already exists.

## Evidence hierarchy

When claims conflict, prefer:

1. passing current validation evidence;
2. current target workspace source/configuration;
3. active workspace profile/policy;
4. verified checkpoints/proofs;
5. verified historical repairs;
6. curated indexed reference knowledge;
7. patterns/examples;
8. model inference.

Reference/indexed knowledge is for discovery and pattern recognition. It must never be promoted into current workspace truth without live evidence.

## Completed reasoning architecture

The bounded reasoning roadmap has reached the runtime-integration boundary. Existing capabilities now cover:

- retrieval mode and typed query planning;
- evidence requirements;
- conflict and insufficient-evidence stopping behavior;
- guard candidate adjudication;
- bounded investigation expansion;
- explanation request construction and verdict/authority immutability;
- governed read-only workspace-rule proposal generation;
- optional proposal candidate transport through the LLM/provider/controller path;
- optional proposal serialization through the normal `/reasoning/run` response.

The normal `/reasoning/run` path remains the reasoning boundary. Do not add a competing endpoint, command, planner, or proposal engine merely to support persistent runtime behavior.

# Current next milestone — Persistent Runtime Integration

## Milestone objective

Build the host runtime around the completed reasoning layer so a normal user conversation can continue across multiple actions, failures, retries, checkpoints, and resume events without moving reasoning, verdict, validation, or governance authority into the runtime.

The runtime should coordinate work over time. It should not become another reasoning model or deterministic guard engine.

Target relationship:

```text
User conversation
      |
      v
Persistent Runtime
  session/task lifecycle
  workspace state refresh
  tool orchestration
  checkpoint/resume
  retry/recovery
  lifecycle evidence
      |
      v
Existing /reasoning/run boundary
      |
      v
Reasoning + Retrieval + Guards + Validation + Governance
      |
      v
Structured result / explanation / optional governed proposal
      |
      v
Persistent Runtime updates task/session state
      |
      v
Normal user response / next action
```

## Non-goals for this milestone

Do not introduce any of the following as part of runtime integration:

- a second reasoning planner;
- a second guard selector or verdict path;
- autonomous `PASS` / `FAIL` inference;
- automatic workspace-rule application;
- unrestricted file repair;
- a new generic memory system without proven need;
- passive learning from model output;
- a duplicate repository/worktree architecture;
- a new UI merely to expose runtime state;
- broad scheduling/background-agent features before the core lifecycle works.

## Runtime responsibilities

The persistent runtime may own only host-runtime concerns:

```text
session identity and lifecycle
current task/objective identity
current target workspace reference
ordered reasoning/tool actions
bounded retry state
checkpoint metadata
resume/recovery state
lifecycle/event receipts
current progress summary derived from evidence
```

It must not own:

```text
guard truth
validation truth
write authorization
workspace policy authority
reasoning-plan semantics
proposal approval
current workspace facts without reinspection
```

# Implementation plan

## Phase 0 — Re-establish live architecture and runtime ownership

Before writing runtime code, inspect current `main` and prove what already exists.

Required inspection:

1. verify repository root, branch, HEAD, and dirty state;
2. inspect current runtime-related modules, including any existing `runtime/`, behavior contracts, server/controller entry points, session state, memory/checkpoint code, tool orchestration, and tests;
3. trace the active `/reasoning/run` entry from HTTP/API boundary to `RequestController`;
4. search for existing session/task IDs, checkpoint records, retry loops, runtime state stores, and orchestration adapters;
5. distinguish active runtime code from historical, test-only, reference, generated, or abandoned paths;
6. identify exactly one owner for each existing runtime concern;
7. report gaps before implementation.

Do not create a new `runtime` subsystem merely because this plan names one. Extend proven active owners when they already exist.

Phase 0 completion evidence:

```text
active runtime map
existing owner per concern
missing capabilities
no duplicate owner introduced
exact implementation surface for Phase 1
```

## Phase 1 — Define the minimal runtime lifecycle contract

Create or extend the smallest typed contract required to represent persistent execution.

The contract should cover only lifecycle state that the host must own. The exact names must fit the existing codebase, but conceptually include:

```text
session
  session_id
  workspace identity/reference
  created/resumed/completed state

task/objective
  task_id
  user objective
  current status
  active reasoning request/result reference
  bounded attempt count

lifecycle event
  event_id
  session_id
  task_id when applicable
  event type
  timestamp
  evidence/result reference
  error/recovery classification when applicable

checkpoint
  session_id
  task_id
  last completed authoritative step
  current workspace/Git identity snapshot
  evidence/result references
  resumable state only
```

Required lifecycle events should be derived from actual owners, but the minimum useful set is expected to cover:

```text
session_started
session_resumed
workspace_refreshed
task_started
reasoning_requested
reasoning_completed
tool_started
tool_completed
validation_observed
checkpoint_saved
retry_scheduled_or_recorded
task_completed
task_blocked
```

Rules:

- events describe what occurred; they do not replace guard/evidence records;
- checkpoint data is resumable context, not proof that old workspace facts remain true;
- schemas/types must reject fabricated verdict or authorization fields;
- session/task status must have one canonical owner.

Phase 1 validation:

- focused contract tests;
- serialization/deserialization tests if persisted;
- invalid-state/forbidden-authority tests;
- duplicate-owner scan.

## Phase 2 — Add the smallest persistent session/task state owner

Implement or extend one canonical runtime state owner.

It must support:

```text
start session
resume session
start task
record lifecycle event
record reasoning result reference
record tool/result reference
record bounded failure/retry state
save checkpoint
mark task blocked/completed
```

Persistence choice must follow existing repository architecture. Do not introduce SQLite, JSONL, filesystem state, or another store merely because it is convenient; first prove which persistence mechanism the current project already owns or requires.

State rules:

- writes are runtime metadata writes, not target-workspace mutation;
- runtime state must live outside the inspected target workspace unless project architecture explicitly defines otherwise;
- secrets and raw provider credentials are never persisted;
- current workspace truth is not copied into durable state as permanently valid fact;
- source/hash/Git facts retained in a checkpoint must be revalidated on resume.

Phase 2 validation:

- state transition tests;
- restart/reopen persistence test;
- no target-workspace mutation test;
- corrupt/missing state handling;
- concurrent/duplicate task protection if the existing runtime can race.

## Phase 3 — Wire the runtime to the existing reasoning boundary

The runtime must call the existing reasoning path rather than reconstruct planning internally.

Expected control flow:

```text
runtime receives user objective
-> resolve/refresh session + target workspace identity
-> build one normal reasoning request
-> invoke existing reasoning/controller boundary
-> receive deterministic result + explanation + optional proposal
-> record lifecycle/result references
-> decide whether the task is complete, blocked, or requires another explicitly justified host action
```

Restrictions:

- do not parse free-form explanation text to create authority decisions;
- do not reinterpret a deterministic verdict;
- do not auto-apply an optional proposal;
- do not copy planning logic into runtime code;
- do not add a second endpoint solely for persistent execution if direct internal invocation of the existing owner is correct;
- keep query/reason/evidence contracts intact.

Phase 3 validation:

- runtime-to-controller integration tests;
- existing reasoning tests remain green;
- `/reasoning/run` behavior remains compatible;
- optional proposal survives integration without being applied;
- deterministic result remains immutable through runtime handling.

## Phase 4 — Checkpoint and resume with live workspace revalidation

A resumed session must not treat its checkpoint as current truth.

Resume sequence:

```text
load checkpoint
-> resolve current target workspace again
-> inspect current Git/workspace identity required by the task
-> compare checkpoint snapshot to current state
-> mark stale assumptions/context explicitly
-> keep still-valid task constraints/objective
-> rebuild bounded runtime context
-> continue through the existing reasoning boundary
```

Checkpoint purpose:

- remember where execution stopped;
- preserve objective/task identity;
- preserve references to verified results already produced;
- make previously completed work visible;
- avoid repeating completed operations unless evidence requires reactivation.

Checkpoint must not:

- certify that source files remain unchanged;
- silently preserve a stale `PASS` as current proof;
- make historical model text authoritative;
- reactivate completed work without a conflict/change trigger.

Phase 4 validation scenario:

1. start session/task;
2. obtain a deterministic result;
3. save checkpoint;
4. stop runtime;
5. alter relevant workspace/Git state in a controlled fixture;
6. resume;
7. prove stale state is detected;
8. prove the objective/task context remains available;
9. prove live inspection/reasoning is used before a new current claim.

## Phase 5 — Bounded failure recovery and retry behavior

Recovery should be evidence-driven, not a blind loop.

Classify failures before retrying:

```text
transient tool/provider failure
validation failure
insufficient evidence
workspace changed
policy/authority blocked
invalid model contract
runtime state/persistence failure
non-retryable implementation defect
```

Retry rules:

- every retry must have a recorded cause;
- bounded attempt count;
- same unchanged failure must not loop indefinitely;
- policy/authority denial is not retryable unless authority changes;
- validation failure is not converted into success by retry;
- insufficient evidence should request/collect the missing evidence only when a real bounded path exists;
- runtime recovery must never broaden target workspace scope silently.

Phase 5 validation:

- transient failure recovers once permitted;
- repeated identical failure stops at bound;
- policy denial does not loop;
- workspace-change recovery forces reinspection;
- completion cannot occur after an unresolved failure.

## Phase 6 — Tool orchestration boundary

Only after the lifecycle and recovery path works, connect host-owned tool sequencing where the current architecture requires it.

Rules:

- use the typed tool registry/capabilities already owned by the system;
- preserve read/write classification and governance;
- tool results become evidence only according to their actual authority;
- every write-capable action remains gated by existing LBE/governance authority;
- do not let the runtime invent tools from model text;
- record tool start/result lifecycle receipts without duplicating the tool's authoritative evidence record.

Do not implement broad autonomous repair in this phase unless a separately approved repair milestone explicitly authorizes it.

## Phase 7 — End-to-end persistent runtime proof

The milestone is not complete until a real controlled lifecycle is proven.

Minimum end-to-end proof:

```text
1. start runtime/session
2. submit a normal user problem against a resolved workspace
3. runtime creates/updates one task
4. runtime invokes the existing reasoning path
5. deterministic guard/validation result is preserved
6. explanation is returned normally
7. optional proposal, when present, remains read-only
8. runtime records lifecycle state and checkpoint
9. stop runtime
10. change or preserve workspace state according to the test case
11. resume same session/task
12. runtime revalidates current workspace identity/state
13. stale checkpoint assumptions are not treated as truth
14. completed authoritative steps are not repeated unnecessarily
15. bounded recovery handles one injected transient failure
16. task reaches COMPLETED only when its evidence-backed completion predicate is satisfied
```

Required proof artifacts should use existing repository conventions. Do not invent a new proof directory unless the project requires one.

# Milestone completion criteria

Persistent Runtime Integration is complete only when all of the following are proven:

```text
one canonical runtime session/task owner exists
AND no duplicate reasoning/verdict/governance authority was created
AND normal user requests enter through the persistent runtime and reach the existing reasoning layer
AND reasoning results remain deterministic-authority preserving
AND checkpoint/resume survives process interruption
AND resume revalidates current workspace state
AND stale checkpoint facts cannot become current truth
AND retry/recovery is bounded and classified
AND write-capable actions remain governed
AND optional proposals remain read-only until separately approved
AND focused + full repository tests pass
AND an end-to-end stop/resume proof passes
AND git diff --check is clean
AND final working tree contains only intended changes
```

Do not declare this milestone complete from unit tests alone.

# Recommended implementation slicing

Do not implement the entire runtime milestone in one patch. Use clean sequential slices, each based on current `main` and validated before the next:

```text
Slice R1: live runtime ownership audit + lifecycle contract
Slice R2: canonical session/task state owner + persistence
Slice R3: runtime -> existing reasoning boundary integration
Slice R4: checkpoint/resume + workspace revalidation
Slice R5: bounded retry/recovery
Slice R6: governed tool orchestration integration where required
Slice R7: end-to-end persistent runtime acceptance proof
```

Each slice must preserve compatibility and must not pre-implement later slices without a proven dependency.

# First task for the next agent

Start with **Slice R1 only**.

Required behavior:

1. sync/inspect current `main` and verify the reasoning baseline has landed;
2. read this project context plus the current roadmap/status/implementation docs;
3. inspect all existing runtime/session/mode/checkpoint/memory/orchestration code and tests;
4. trace the active reasoning boundary;
5. produce the exact runtime ownership map and smallest lifecycle-contract change;
6. add/update focused tests first when the contract can be expressed deterministically;
7. implement only the lifecycle contract/foundation proven necessary for R1;
8. run focused tests, then the full suite;
9. run `git diff --check` and inspect final status/diff;
10. stop after R1 is proven. Do not proceed automatically into persistence, resume, retries, or tool orchestration.

If inspection shows that an equivalent lifecycle contract or runtime owner already exists, extend it instead of creating a parallel implementation.

## Workspace-rule lifecycle

A verified finding may lead to a workspace-specific proposal, not directly to a global guard.

```text
verified finding
-> workspace-rule candidate
-> equivalence/contradiction check
-> exact profile diff
-> user approval
-> LBE governance authorization
-> application
-> activation validation
-> provenance
```

Proposal generation is read-only. Never call or recreate approval/application paths merely because a proposal exists.

## Repository work discipline

For every implementation/debugging task:

1. establish repository root, branch, HEAD, and dirty state;
2. map the smallest relevant active path;
3. inspect contracts/tests/registries before editing;
4. prove the active owner and check for duplicate/parallel implementations;
5. make the smallest correct change;
6. add or update focused regression coverage when appropriate;
7. run focused validation, then project-level validation required by the claim;
8. perform a bounded duplicate-authority/regression scan;
9. remove temporary artifacts;
10. run `git diff --check` and `git status --short` before completion.

Do not create extra workspace copies or worktrees merely to inspect or implement a task. Do not leave patch scripts, transient test-output files, generated state, caches, or local credentials staged.

## Completion contract

A task is complete only when:

```text
intended change exists
AND the active path uses it when applicable
AND required validation passes
AND observed behavior matches the objective
AND no in-scope blocker remains
AND the working tree contains no accidental artifacts
```

A passing command alone is not completion. A passing unit test alone is not runtime proof when the claim is runtime/user-visible behavior.

## Agent reporting

Keep final reports compact. State:

- what requirement or defect was addressed;
- exact files changed;
- validation evidence;
- remaining blocker/risk, if any.

Do not restart Q&A about architecture that is already documented here unless live repository evidence contradicts the document.