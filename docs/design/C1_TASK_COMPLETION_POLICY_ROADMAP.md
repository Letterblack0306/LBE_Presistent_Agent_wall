# C1 Task Completion Policy Roadmap

Updated: 2026-08-10
Status: Documentation-first architecture checkpoint

## Purpose

Resolve the C1 blocker discovered after C0: the repository can persist an immutable `TaskCompletionContract`, but no existing LBE owner currently maps runtime/task policy to the exact semantic `evidence_kind` requirements that such a contract requires.

This document defines the smallest new policy boundary needed to make that ownership explicit without creating a second completion gate, validation engine, or provider-controlled requirement path.

## Evidence-backed finding

Current source proves:

- C0 now persists authoritative typed `permission` and `runtime_policy` session facts and resolves R6B `ModeDecision` on the governed gateway path;
- provider `COMPLETED` is provisional for coding tasks;
- model-selected validation requirements are forbidden;
- `TaskCompletionContract` requires exact `CompletionRequirement.evidence_kind` values;
- `CodingCompletionRuntime.persist_contract()` persists an already-resolved contract and intentionally does not derive policy;
- behavior contracts expose broad categories such as current workspace evidence and validation-before-acceptance, but do not define exact completion evidence kinds;
- no production source currently constructs `TaskCompletionContract` / `CompletionRequirement` for a normal coding task.

Therefore C1 cannot safely derive requirements from provider prose, generic behavior names, arbitrary CLI arguments, raw command success, or opaque policy IDs.

## Architectural decision

Introduce one explicit **LBE-owned task completion policy catalog** at the canonical task-establishment boundary.

This catalog is configuration/policy data, not a new completion evaluator.

The ownership chain becomes:

```text
LBE task establishment
        |
        +-- operation/task class
        +-- resolved C0 ModeDecision
        +-- authoritative session/runtime policy
        v
LBE Task Completion Policy Catalog
        |
        +-- exact declared CompletionRequirement templates
        v
TaskCompletionContract
        v
existing immutable persistence
        v
C2 trusted producers
        v
existing completion gate
```

The catalog owns only the declaration of what semantic proof a supported task class requires. It does not execute validation, classify evidence, or decide completion.

## Why this is not a parallel completion resolver

The existing owners remain unchanged:

- C0/R6B owns effective runtime mode and capabilities;
- R6C owns authorization decisions;
- R6E owns governed tool orchestration;
- `CodingCompletionRuntime` owns contract persistence/load and provisional coding completion behavior;
- producer-bound evidence storage owns durable semantic producer results;
- the existing completion gate owns final contract-vs-evidence evaluation.

The new catalog fills the one missing policy-data responsibility: exact requirement declaration for a supported task class.

## Catalog contract

The smallest useful policy record should contain:

```text
policy_id
operation_id / task_class
applicable_mode
requirements[]
    requirement_id
    evidence_kind
    description
```

Requirements are deterministic repository-owned policy data.

They must not be supplied or widened by:

- provider/model output;
- `ReasoningPlan.validation_requests`;
- request arguments;
- CLI `--evidence-kind` style input;
- raw tool/command exit status;
- checkpoint/history prose;
- opaque `permission_policy_id`, `evidence_policy_id`, or profile IDs.

## Exact evidence-kind rule

C1 must not invent generic evidence kinds merely to produce a non-empty contract.

A completion-policy entry may reference an `evidence_kind` only when that semantic kind is deliberately declared as part of the LBE task policy and has a bounded C2 producer design.

If no declared policy entry exists for a task/operation, governed coding completion fails closed and remains incomplete. The provider cannot substitute a requirement.

This means the first code slice may introduce the catalog and fail-closed contract-establishment path before every future coding task class has a completion template.

## C1 code slice

### C1.1 Define the task completion policy type/catalog

Add one canonical runtime policy data structure that:

- is owned by LBE runtime/task establishment;
- maps a supported operation/task class plus authoritative runtime mode to exact completion requirements;
- is deterministic and provider-independent;
- rejects duplicate policy IDs and ambiguous mappings;
- has no tool execution or evidence classification behavior.

Do not create a generic free-form resolver accepting arbitrary caller requirements.

### C1.2 Establish the contract once per normal coding task

On the normal governed coding path:

1. use the already-resolved C0 `ModeDecision` and bounded registered operation identity;
2. select the matching LBE-owned completion policy entry;
3. construct `TaskCompletionContract` from that entry;
4. persist it through existing `CodingCompletionRuntime.persist_contract()`;
5. on resume/retry/provider switch, load and reuse the existing immutable contract;
6. reject incompatible replacement.

If the task has no declared completion policy, fail closed before claiming completion.

### C1.3 Preserve task identity and provider independence

The persisted contract must remain bound to:

- session;
- task;
- project/workspace identity;
- original requirement set.

Provider/model switching must not alter the contract.

### C1.4 Keep C2 separate

C1 does not implement semantic validation producers.

C2 will add trusted registered producers only for evidence kinds already declared by supported C1 policy entries.

Until required producer evidence exists, the existing completion gate must keep the task incomplete.

## Initial policy population rule

Do not guess a universal coding contract.

For each first supported policy entry, require an explicit bounded task/operation semantics and an identified future producer for every exact `evidence_kind` before enabling that entry in normal production execution.

If the current `reasoning.inspect` coding path is not semantically sufficient to determine a concrete completion contract, leave it fail-closed rather than assigning fabricated requirements.

## Non-goals

C1 must not:

- implement C2 producers;
- implement `lbe session validate`;
- introduce another completion gate;
- let provider/model choose evidence kinds;
- interpret raw command success as semantic proof;
- reinterpret broad behavior-contract categories as exact evidence kinds without explicit policy declaration;
- add unrestricted shell/tool execution;
- replace C0 policy ownership;
- alter R6C/R6E ownership.

## Acceptance gate before C2

Before C2 begins, prove:

1. a supported governed coding task receives exactly one immutable contract from LBE-owned task policy;
2. no provider/request field can choose or widen its requirements;
3. unsupported task/operation classes fail closed rather than receiving fabricated requirements;
4. contract persistence uses the existing completion runtime/storage path;
5. retry/resume loads the same contract;
6. provider switching leaves the contract unchanged;
7. incompatible replacement is rejected;
8. C1 performs no validation production or evidence classification;
9. the existing completion gate remains the only final evaluator;
10. no duplicate completion/session/policy authority was introduced.

## Dependency order

```text
C0 authoritative runtime-policy composition  [complete]
        v
C1 LBE task completion policy catalog
        v
immutable task completion contract establishment
        v
C2 trusted semantic validation producers
        v
producer-bound completion evidence
        v
existing completion gate
        v
C3 thin session validate
```

## Implementation stop condition

If implementation cannot identify a bounded task/operation with deliberately declared exact evidence kinds and corresponding C2 producer semantics, stop at the fail-closed catalog/contract boundary and report the missing task-policy entry. Do not invent proof vocabulary to force C1 to appear complete.
