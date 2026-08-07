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

The intended reasoning flow is:

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
```

Never create a second verdict path, approval path, mutation authority, proposal engine, or state owner when an existing owner already exists.

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

## Current reasoning architecture

The reasoning layer is intentionally bounded. Existing modules include planning for:

- retrieval mode and typed queries;
- evidence requirements;
- conflict handling;
- guard candidate adjudication;
- bounded investigation expansion;
- explanation request construction and immutability;
- read-only governed workspace-rule proposal generation.

The normal `/reasoning/run` path is the runtime boundary for the integrated reasoning feature. Do not add a competing endpoint or command merely to expose a new reasoning capability unless the architecture explicitly requires one.

## Current roadmap direction

Follow `docs/design/LLM_REASONING_LAYER_ROADMAP.md`, `docs/CURRENT_STATUS.md`, and `docs/IMPLEMENTATION_PLAN.md`, but verify every claim against live source before acting.

The active direction is to finish integrated LLM/controller behavior while preserving deterministic verdict, validation, and governance ownership. Persistent runtime/session concerns remain separate from reasoning ownership.

Do not silently implement deferred capabilities as part of an unrelated slice.

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