# Completion Contract Research Evidence

Updated: 2026-08-10
Status: Documentation-only research checkpoint

## Why this document exists

This repository already has completion-gate persistence and producer-bound completion-evidence persistence, but current inspection found an earlier missing production dependency: a real coding task does not yet establish its authoritative completion contract.

This document records the evidence behind the revised implementation order before any further agent/CLI code change.

## Research discipline used

For this architecture decision the sequence was:

1. consult the relevant GPT-Knowledge reference;
2. verify current GitHub source and main head;
3. inspect local repository/BirdEye evidence where needed;
4. compare with primary live workflow/runtime documentation;
5. update docs/plan before implementation.

This is an engineering research discipline, not a new runtime blocker.

## GPT-Knowledge reference

Primary internal reference:

- `Letterblack0306/GPT-Knowledge/ai-agents/lbe-cli-control-plane-provider-boundary.md`
- verified blob during research: `f19e97f8da7495405fe143b695679f7535a0808c`

Relevant invariant:

```text
Provider reasons.
External agent proposes and interacts.
LBE runtime orchestrates.
CLI/API transport requests capabilities.
Guards detect.
Workspace evidence supplies current facts.
LBE governance authorizes.
Validation proves.
Persistent session state belongs to LBE.
User-configured policy decides when another confirmation is required.
```

The reference assigns deterministic validation/completion requirements and completion proof to LBE rather than the provider.

Companion research study:

- `Letterblack0306/GPT-Knowledge/ai-agents/studies/lbe-completion-contract-and-validation-evidence-study.md`

## Verified repository state

Repository:
- `Letterblack0306/LBE_Presistent_Agent_wall`

Main head verified during research:
- `3deef36afd0b635f43d234fce6672d9de78e086c`

Relevant merged milestones already present:

- PR #44: durable immutable task completion-contract persistence;
- PR #45: coding gateway keeps provider `COMPLETED` provisional as `AWAITING_VALIDATION`;
- PR #46: durable producer-bound task completion-evidence persistence.

## Current-source findings

### Model validation selection is deliberately forbidden

`lbe_guard_inspector/request_controller.py` rejects non-empty `ReasoningPlan.validation_requests` with `MODEL_VALIDATION_REQUEST_FORBIDDEN` because deterministic validation selection belongs to LBE.

Therefore the completion contract must not be derived from provider-selected validation IDs.

### Completion runtime persists resolved contracts but does not derive policy

`lbe_guard_inspector/runtime/completion_runtime.py` exposes `persist_contract()` for an **already-resolved** `TaskCompletionContract` and explicitly states that the method does not derive policy.

Repository inspection found no production caller establishing such a contract for a normal coding task at the time of this research.

### Completion evidence persistence is producer-bound by design

PR #46 added durable evidence identity including semantic kind, producer ID and operation ID. `CodingCompletionRuntime.load_evidence()` remains read-only so the provider, CLI, and completion gate do not classify evidence themselves.

### Generic execution receipts are supporting facts, not semantic proof

Existing command/tool result storage can preserve command exit status and structured tool success. That does not prove task-specific semantics such as `focused_test`, `source_change`, or other future completion requirement kinds.

A raw command exit code must not be relabeled as semantic completion evidence by a model or CLI caller.

## External primary references

### GitHub required status checks

Primary docs:

- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks

Observed property:

- requirements exist independently of individual check executions;
- checks/status producers report outcomes;
- required checks must satisfy the gate before the protected transition;
- an expected source/app can be selected for required checks.

Architecture lesson for LBE:

```text
completion requirement
!= validation producer
!= completion gate
```

### LangGraph persistence and durable execution

Primary docs:

- https://docs.langchain.com/oss/python/langgraph/persistence
- https://docs.langchain.com/oss/python/langgraph/functional-api

Observed property:

- state is bound to thread/task identity;
- checkpoints and task writes are persisted during execution;
- resume uses durable recorded state rather than reconstructing the workflow from conversational prose.

Architecture lesson for LBE:

Once resolved, completion requirements should become durable task state and survive restart/provider switch.

### Temporal durable execution

Primary docs:

- https://docs.temporal.io/

Observed property:

- workflow execution state survives process and infrastructure failures;
- execution resumes from persisted workflow state/history.

Architecture lesson for LBE:

Task completion requirements belong to the persistent lifecycle, not a transient provider turn.

## Revised dependency order

The next runtime/CLI dependency order is now:

```text
coding task/session established
        |
        v
LBE-owned task/policy boundary resolves completion requirements
        |
        v
immutable TaskCompletionContract persisted
        |
        v
registered governed validation producer(s) execute
        |
        v
producer-bound semantic completion evidence persisted
        |
        v
existing evaluate_completion() gate evaluates contract + evidence
        |
        v
CLI/API exposes deterministic result
```

`lbe session validate` is therefore **not** the next implementation step by itself.

## What remains unresolved

Research has not yet proven which existing LBE component is the canonical production owner for resolving completion requirements.

Before creating a new resolver, inspect and reconcile:

- canonical task-establishment/request boundary;
- persisted session policy/profile identifiers;
- mode/capability contracts;
- behavior contracts;
- evidence/validation policy concepts;
- registered validation capability metadata.

Do not create a generic parallel `CompletionContractResolver` until evidence shows that no existing owner can provide the required semantics.

## Plan update

Before `session validate`, implementation must complete these slices in order:

### C1 — Establish production completion contract

- identify existing authoritative task/policy owner;
- deterministically map its requirements to `TaskCompletionContract`;
- persist once per task;
- reject incompatible replacement;
- prove contract survives resume/provider switch.

### C2 — Trusted semantic validation producers

- register only required producer classes;
- bind each supported completion-evidence kind to a trusted producer;
- persist producer/operation identity;
- do not allow provider/CLI evidence relabeling;
- preserve FAIL/STALE results.

### C3 — Thin `lbe session validate`

- load persisted contract;
- load trusted stored evidence;
- call existing `CodingCompletionRuntime.finalize()`;
- expose result/status only;
- do not add a second completion/evidence policy engine to CLI.

### C4 — Remaining CLI families

After the runtime service path exists:

- `lbe provider check`;
- `lbe code`;
- `lbe audit`;
- `lbe investigate`.

### C5 — R7 installed/normal-path proof

Prove coding, provider switch, resume after external workspace change, audit read-only behavior, escalation, and deterministic completion from the installed/normal execution path.

## Acceptance evidence required before C1 implementation

Before code changes begin, verify again:

- current `main` head and relevant files through GitHub;
- no newly added production completion-contract owner already solves the gap;
- current local diff through BirdEye/live Git evidence;
- chosen owner does not duplicate session, policy, permission, evidence, or completion authority.

## Non-goals

This research checkpoint does not authorize:

- CLI-owned evidence classification;
- model-selected validation IDs;
- arbitrary caller-supplied PASS evidence;
- raw command success as semantic completion proof;
- a second completion gate;
- a second task/session controller;
- implementation changes in this documentation PR.