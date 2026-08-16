# Current Implementation Gate

Status: **PASS — R4 CHECKPOINT/RESUME/REHYDRATION ACCEPTED — NEXT PHASE LOCKED**

Current phase: `R4_CHECKPOINT_RESUME_ACCEPTANCE`

Current slice: `PROVE_CHECKPOINT_RESTART_REHYDRATION_AND_STALE_STATE_INVALIDATION`

This file is the human-readable authority paired with `.lbe/governance/implementation-gates.json`.

## Active plan

```text
active_plan: docs/acceptance/R4_CHECKPOINT_RESUME_ACCEPTANCE_GATE.md
checkpoint: docs/acceptance/R4_CHECKPOINT_RESUME_ACCEPTANCE_CHECKPOINT.md
kind: accepted acceptance proof, not implementation
implementation_allowed: false
architecture_changes_allowed: false
next_phase_locked: true
required_evidence_level: INTEGRATION
status: PASS
```

## Accepted owner path

```text
SessionMemoryRuntimeBridge.start_or_resume
 -> SessionMemoryAdapter.rehydrate
 -> memory.context.rehydrate_context
 -> inspect current Git state
 -> load VERIFIED records
 -> invalidate changed source-backed records
 -> revalidate protected checkpoint
 -> return current context packet
```

Checkpoint persistence remains owned by:

```text
SessionMemoryRuntimeBridge.checkpoint
 -> SessionMemoryAdapter.checkpoint_compaction
 -> WorkspaceMemoryStore
```

No second checkpoint/session/memory owner was introduced.

## Acceptance result

R4 is accepted at the required integration level.

The decisive repository-owned integration discriminator passed:

```text
tests/test_session_resume_runtime.py::test_resume_invalidates_changed_source_fact_and_reports_changed_head
1 passed
command_hash: 75671F43AA1BE3A1DA1F67BFC34CFD39CD30326FC3AEA1CCE5C55393DF66A779
```

It proves the required external-change/resume behavior:

1. a source-backed fact is VERIFIED before checkpoint;
2. an active task and checkpoint constraint are persisted;
3. the source is changed and committed externally, producing a new Git HEAD;
4. reconstruction resumes the same task/session path;
5. the old source-backed fact becomes `STALE`;
6. the stale fact is absent from resumed `verified_facts`;
7. checkpoint HEAD revalidation reports `MISMATCH`;
8. protected checkpoint status becomes `INELIGIBLE`;
9. current task status survives;
10. checkpoint constraints survive.

## Session/provider persistence

Existing repository tests also cover restart persistence of:

```text
session_id
project_workspace_id
canonical workspace root
mode
provider_id
provider_model
active_profile_id
permission_policy_id
evidence_policy_id
task_id / task status
```

## Compaction/history authority

Current source contract confirms compaction/history cannot become current workspace truth:

- `SessionMemoryAdapter` accepts structured deterministic evidence only and explicitly does not parse assistant prose or compaction summaries into verified workspace facts;
- `rehydrate_context()` queries only `ValidationStatus.VERIFIED` records;
- source-backed records are hash-revalidated before inclusion;
- resumed packets explicitly state: `Do not use assistant reasoning or compaction summaries as authority.`

This satisfies the R4 authority requirement without adding a new memory owner.

## Focused regression

```text
python -m pytest -q tests/test_session_resume_runtime.py tests/test_session_memory_runtime.py tests/test_session_memory_adapter.py tests/test_checkpoint_eligibility.py

37 passed in 34.45s
command_hash: DDF73255339D42EE149AC6D15920AA108F40FDB530738A1364268A9E2806B9DD
```

No runtime or test implementation source changed during R4 acceptance.

## Harness-only failures

Two earlier ad hoc embedded-Python LoopTool probes failed before product execution because command transport corrupted Python quoting/indentation.

```text
classification: TEST_HARNESS_TRANSPORT_FAILURE
product implication: none
```

The acceptance method was corrected to repository-owned tests. These harness failures are not R4 product failures.

## R4 classification

```text
R4 checkpoint/resume/rehydration: PROVEN_COMPLETE
```

## Next dependency

The earliest remaining roadmap candidate is:

```text
R5 bounded classified recovery
current classification: IMPLEMENTED_NOT_ACCEPTED
active: NO
```

R5 must not activate automatically from this PASS. A separate machine/human acceptance gate must define its observable, falsifier, owner path, and required evidence level before execution.

## Readiness

```text
project_user_ready: NO
release_ready: NO
next_phase_locked: true
```

R4 PASS does not imply overall project or release readiness.
