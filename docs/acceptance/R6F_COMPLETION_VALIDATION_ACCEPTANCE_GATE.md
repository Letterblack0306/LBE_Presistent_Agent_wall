# R6F Completion and Validation Acceptance Gate

Status: **OPEN — ACCEPTANCE PROOF ONLY — RELEASE PATH ACTIVE — NEXT PHASE LOCKED**

```text
phase: R6F_COMPLETION_VALIDATION_ACCEPTANCE
slice: PROVE_EVIDENCE_OWNED_TERMINAL_COMPLETION_THROUGH_PERSISTENT_CODING_RUNTIME
base_sha: fdb256c09f331610e596f12fdca008785b9518a4
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
```

## Selection rationale

The user authorized proceeding toward release. Canonical dependency order still requires R6F completion/validation before CLI normal-path, R7 installed end-to-end proof, and release/package readiness. Existing source already contains the completion owner; this is acceptance-first and does not declare a defect.

## Acceptance question

Can the existing persistent coding runtime prove that provider/model reasoning success remains provisional, terminal completion is determined only from an explicit persisted completion contract plus producer-bound structured evidence, stale/missing/failed evidence blocks or fails completion, and only a fully satisfied claimed completion persists canonical task state as COMPLETED?

## Existing owners

```text
runtime.completion_gate.evaluate_completion
runtime.completion_runtime.CodingCompletionRuntime
runtime.task_completion_policy
runtime.completion_evidence_producers
memory.completion_contracts.TaskCompletionContractPersistence
memory.completion_evidence.TaskCompletionEvidencePersistence
SessionMemoryRuntimeBridge
```

## Reuse decision

```text
REUSE
```

Do not introduce another completion gate, task-state owner, validation authority, evidence store, or provider-authored DONE authority.

## Required observables

1. reasoning outcome `COMPLETED` remains provisional as RUNNING/AWAITING_VALIDATION;
2. model/provider completion prose without required evidence cannot produce READY/COMPLETED;
3. stale evidence cannot satisfy a required completion requirement;
4. deterministic failed evidence yields FAILED and persisted task failure;
5. missing evidence yields BLOCKED and persisted incomplete task state;
6. all required evidence must PASS and completion must be explicitly claimed before READY;
7. READY persists canonical task status COMPLETED with `VALIDATED_COMPLETION`;
8. persisted contract/evidence remains bound to session/task/workspace identity;
9. validation evidence classification remains producer-owned, not CLI/provider-owned;
10. no second completion/task-state authority is introduced;
11. focused completion/runtime/memory regression passes on the exact acceptance head;
12. runtime/test implementation source remains unchanged unless a real falsifier is proven.

## Falsifier

R6F cannot PASS if provider/model prose can directly establish terminal completion, stale/missing evidence satisfies requirements, failed validation can still complete, READY can occur without all required PASS evidence plus a completion claim, completion changes a different session/task/workspace, or another completion/state authority is required.

## Evidence ladder

```text
source-owner inspection
-> repository-owned completion contract/gate/evidence/runtime tests
-> persistent coding provisional-completion discriminator
-> missing/stale/failed evidence stop discriminators
-> all-pass READY -> canonical COMPLETED discriminator
-> persistence/session/workspace binding proof
-> focused regression
-> diff/scope/worktree proof
-> checkpoint
```

## Forbidden work

- runtime/test implementation before a real defect is proven;
- CLI/R7/release publishing while R6F is OPEN;
- new completion/validation/task-state owner;
- model/provider-authored completion authority;
- version bump/tag/package publish;
- architecture changes.

## Completion predicate

PASS only when terminal completion is proven evidence-owned through the existing persistent coding runtime with no falsifier. PASS does not auto-activate CLI, R7, or release publication.