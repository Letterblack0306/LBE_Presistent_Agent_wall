# R6F Completion and Validation Acceptance Checkpoint

```text
phase: R6F_COMPLETION_VALIDATION_ACCEPTANCE
slice: PROVE_EVIDENCE_OWNED_TERMINAL_COMPLETION_THROUGH_PERSISTENT_CODING_RUNTIME
status: UNVERIFIED
base_sha: fdb256c09f331610e596f12fdca008785b9518a4
implementation_sha: NOT_APPLICABLE_ACCEPTANCE_ONLY
required_evidence_level: INTEGRATION
next_phase_locked: true
```

## Requirements

- prove reasoning `COMPLETED` remains provisional pending validation;
- prove model/provider claim alone cannot complete;
- prove missing/stale evidence blocks completion;
- prove failed required evidence fails completion;
- prove all required evidence plus explicit claim yields READY;
- prove READY alone promotes canonical persisted task state to COMPLETED/VALIDATED_COMPLETION;
- prove contract/evidence identity remains session/task/workspace bound;
- prove producer-bound evidence classification remains authoritative;
- run focused completion/runtime/memory regression;
- record exact evidence, falsifiers, diff and clean-worktree proof.

## Existing owner

```text
evaluate_completion
CodingCompletionRuntime
TaskCompletionContractPersistence
TaskCompletionEvidencePersistence
completion_evidence_producers
SessionMemoryRuntimeBridge
```

## Reuse decision

```text
decision: REUSE
evidence: completion gate/runtime, persisted contracts/evidence and canonical task-state integration already exist; integrated acceptance is missing.
```

## Architecture change

```text
introduced: no
user_authorized: release progression only; no new architecture requested
canonical_docs_updated_first: yes
```

## Validation evidence

```text
source_owner_inspection: PASS
repository_completion_tests: PRESENT_NOT_YET_RUN_ON_GATE_HEAD
provisional_reasoning_completion: NOT RUN
claim_without_evidence_blocked: PRESENT_SEPARATELY_NOT_YET_ACCEPTED
stale_evidence_blocked: PRESENT_SEPARATELY_NOT_YET_ACCEPTED
failed_evidence_fails: PRESENT_SEPARATELY_NOT_YET_ACCEPTED
all_pass_ready: PRESENT_SEPARATELY_NOT_YET_ACCEPTED
canonical_task_completion_persistence: PRESENT_SEPARATELY_NOT_YET_ACCEPTED
identity_binding: NOT RUN
focused_regression: NOT RUN
git_diff_check: NOT RUN
worktree_clean: NOT RUN
```

## Falsifier state

```text
observed_falsifier: NONE YET
```

## Unverified

- integrated persistent coding reasoning -> provisional state -> validation -> terminal task-state lifecycle;
- producer/persistence identity binding in the same acceptance path;
- focused regression and final scope/worktree proof.

## Readiness

```text
release_path_authorized: true
release_publish_allowed_now: false
project_user_ready: NO
release_ready: NO
next_phase_locked: true
```
