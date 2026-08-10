# Completion Contract Research Evidence

Updated: 2026-08-10
Status: Documentation-only research checkpoint

## Why this document exists

This repository already has completion-gate persistence and producer-bound completion-evidence persistence, but current inspection found earlier missing production dependencies: a real coding task does not yet establish its authoritative completion contract, and the typed R6B mode policy engine is not yet proven to participate in the normal production request path.

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

Companion research studies:

- `Letterblack0306/GPT-Knowledge/ai-agents/studies/lbe-completion-contract-and-validation-evidence-study.md`
- `Letterblack0306/GPT-Knowledge/ai-agents/reference-derived-agent-architecture.md`

## Verified repository state

Repository:
- `Letterblack0306/LBE_Presistent_Agent_wall`

Main head verified during the first completion-contract research checkpoint:
- `3deef36afd0b635f43d234fce6672d9de78e086c`

Main head verified during the subsequent mode-wiring inspection:
- `74d9142c1da04a23abe3962f79630d02cc1d13a1`

Relevant merged milestones already present:

- PR #44: durable immutable task completion-contract persistence;
- PR #45: coding gateway keeps provider `COMPLETED` provisional as `AWAITING_VALIDATION`;
- PR #46: durable producer-bound task completion-evidence persistence;
- PR #47: completion-contract research and dependency documentation.

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

### R6B mode policy exists but is not wired into the normal production path

`lbe_guard_inspector/runtime/mode_controller.py` defines the typed `ModeRequest`, `ModeDecision`, `resolve_mode()`, allowed behaviors, and derived capabilities.

Current production search across `lbe_guard_inspector/**/*.py` returned:

```text
MODE_HIT_COUNT=0
```

for consumers of:

- `ModeRequest(`
- `ModeDecision`
- `resolve_mode(`

outside the mode-controller module itself.

The current `AgentRequestEnvelope` carries a `mode`, and `GovernedAgentGateway._validate_identity()` verifies that request mode matches persisted session mode. That establishes identity consistency, but it does **not** prove that the effective runtime mode, behaviors, and capabilities were resolved through R6B policy in the actual gateway path.

This makes production mode-policy wiring a prerequisite before completion-contract resolution can safely depend on mode/capability semantics.

### Session policy/profile IDs are currently persistence references, not proven completion-policy resolvers

The persisted session schema carries:

```text
active_profile_id
permission_policy_id
evidence_policy_id
```

Current inspection did not find a production loader/resolver that turns these IDs into completion requirements. They must not be treated as resolved completion policy merely because the IDs are persisted.

## Existing behavior-contract evidence

The public behavior vocabulary already contains useful policy semantics:

### `validation_before_acceptance`

- requires validation evidence;
- permits validate/verify/corroborate/cross-check;
- forbids accepting unvalidated output or self-validation;
- assigns authority to independent verification.

### `development_mode_capabilities`

- permits discovery, proposal, candidate testing, proposal validation, and promotion only after validation;
- forbids bypassing validation or promotion without proof.

These contracts support the policy boundary, but current evidence does not show them being resolved through R6B in the normal gateway request path.

## External primary/live references

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

Once resolved, runtime mode/policy and completion requirements should be represented as durable authoritative task/session state rather than reconstructed from provider text.

### OpenHands agent runtime

Primary docs:

- https://docs.openhands.dev/sdk/arch/agent

Observed property:

- model responses become events;
- action confirmation is a distinct runtime check;
- execution produces observation events;
- runtime conversation state records waiting/continuation state;
- the agent logic itself is stateless between steps and consumes event history.

Architecture lesson for LBE:

Provider reasoning and runtime authorization/execution state should remain separate, with the runtime owning policy transitions.

### OpenAI Codex CLI approval/execution modes

Primary official/help reference:

- https://help.openai.com/en/articles/11096431

Observed property:

- execution modes determine what the agent may read/write/execute;
- sandbox and approval behavior are runtime configuration, not model-authored authority.

Architecture lesson for LBE:

Mode/capability policy must be part of the real execution path before downstream completion logic relies on it.

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
C0: production R6B mode-policy resolution
    -> effective mode
    -> allowed behaviors
    -> capabilities
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

## What is now resolved

Research has established that the existing R6B mode controller must participate in the real production request path before completion-contract establishment can use mode/capability semantics as authoritative inputs.

Do **not** create a second mode resolver.

## What remains unresolved

Research has still not proven which existing LBE component should map already-resolved runtime/task policy facts into exact `TaskCompletionContract` requirement kinds.

Before creating a new completion resolver, inspect and reconcile:

- canonical task-establishment/request boundary;
- resolved mode/capability decision after C0;
- persisted session policy/profile identifiers;
- evidence/validation policy concepts;
- registered validation capability metadata;
- operation/tool metadata that may supply task-specific required proof.

Do not create a generic parallel `CompletionContractResolver` until evidence shows that no existing owner can provide the required semantics.

## Plan update

Before `session validate`, implementation must complete these slices in order:

### C0 — Wire the existing R6B mode policy into production

- reuse existing `ModeRequest`, `ModeDecision`, and `resolve_mode()`;
- integrate them into the normal request/runtime path rather than creating another resolver;
- derive resolution inputs only from authoritative session/request policy facts;
- reject contradictions between resolved mode and persisted/request identity;
- expose resolved behaviors/capabilities to downstream authorization/context/completion-contract logic;
- prove provider switching does not alter resolved workspace policy;
- prove audit/investigation cannot gain coding capabilities from provider output alone.

C0 does **not** define completion requirement kinds and does not add `session validate`.

### C1 — Establish production completion contract

- identify existing authoritative task/policy owner after C0;
- deterministically map already-resolved policy/task facts to `TaskCompletionContract`;
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

## Acceptance evidence required before C0 implementation

Before code changes begin, verify again:

- current `main` head and relevant files through GitHub;
- no newly added production mode-policy wiring already solves the gap;
- current local diff through BirdEye/live Git evidence;
- chosen integration point does not duplicate session, policy, permission, evidence, or completion authority;
- the existing mode controller remains the sole mode-resolution owner.

## Acceptance evidence required before C1 implementation

Before C1 begins, prove from the installed/normal request path that:

1. R6B mode resolution is actually invoked;
2. the decision is deterministic from authoritative inputs;
3. request/session identity cannot silently contradict the resolved decision;
4. resolved behaviors/capabilities are available to runtime consumers;
5. provider switching does not change the resolved workspace policy;
6. audit/investigation cannot gain coding capabilities through provider output alone.

## Non-goals

This research checkpoint does not authorize:

- CLI-owned evidence classification;
- model-selected validation IDs;
- arbitrary caller-supplied PASS evidence;
- raw command success as semantic completion proof;
- a second completion gate;
- a second task/session controller;
- a second mode resolver;
- implementation changes in this documentation checkpoint.
