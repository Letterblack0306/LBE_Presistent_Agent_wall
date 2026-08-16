# R4 Checkpoint Resume Acceptance Checkpoint

```text
phase: R4_CHECKPOINT_RESUME_ACCEPTANCE
slice: PROVE_CHECKPOINT_RESTART_REHYDRATION_AND_STALE_STATE_INVALIDATION
status: UNVERIFIED

base_sha: 9523cf02f8a2e9248ad87d7f6f4cadef6d959f51
implementation_sha: NOT_APPLICABLE_ACCEPTANCE_ONLY
required_evidence_level: INTEGRATION
next_phase_locked: true
```

## Requirements

- prove checkpoint/restart/resume through existing `SessionMemoryRuntimeBridge` and `SessionMemoryAdapter`;
- preserve session/task/workspace identity and persisted provider/session configuration;
- prove active checkpoint constraints survive restart;
- prove external source/Git changes are re-inspected on resume;
- prove old source-backed facts become `STALE` and are removed from resumed `verified_facts`;
- prove changed HEAD makes the protected checkpoint `INELIGIBLE` with `reactivation_allowed=false`;
- prove compaction/history material is not promoted into current workspace truth;
- introduce no runtime/checkpoint/memory source changes unless a real defect is first proven;
- run focused R4/session-memory regression on the exact acceptance head;
- record exact evidence and falsifiers.

## Existing owner

```text
SessionMemoryRuntimeBridge.start_or_resume
SessionMemoryAdapter.checkpoint_compaction / rehydrate
memory.context.invalidate_changed_sources
memory.context.protected_checkpoint_eligibility
memory.context.rehydrate_context
WorkspaceMemoryStore
```

## Reuse decision

```text
decision: REUSE
evidence: current source/tests already contain the R4 path; missing artifact is dedicated roadmap acceptance evidence.
```

## Architecture change

```text
introduced: no
user_authorized: no new architecture requested
canonical_docs_updated_first: yes
```

## Validation evidence

```text
source_owner_inspection: PASS
checkpoint_change_restart_integration: NOT RUN
session_task_workspace_identity: NOT RUN
constraint_survival: NOT RUN
changed_head_revalidation: NOT RUN
stale_source_fact_invalidation: NOT RUN
stale_fact_removed_from_verified_context: NOT RUN
compaction_not_current_truth: NOT RUN
provider_session_preservation: NOT RUN
focused_regression: NOT RUN
broader_regression_classification: NOT RUN
git_diff_check: NOT RUN
worktree_clean: NOT RUN
```

## Falsifier state

```text
observed_falsifier: NONE YET
```

## Unverified

- bounded integration behavior after an external committed source change;
- exact stale-memory and checkpoint eligibility state;
- focused regression at the R4 acceptance head;
- final workspace/diff proof.

## Document conflicts

```text
none known at activation
```

## Readiness

```text
project_user_ready: NO
release_ready: NO
next_phase_locked: true
```
